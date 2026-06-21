"""FastAPI app — multi-tenant: per-user signup/login, scoped jobs & files.

The web tier validates input and enqueues jobs onto Redis. Long downloads run
in the arq worker.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from collections import defaultdict
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from . import auth, db
from .config import settings
from .schemas import JobRequest, LoginRequest, SignupRequest

app = FastAPI(title="VideoDead", version="2.0.0", docs_url=None, redoc_url=None)

_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limit(key: str, per_minute: int) -> None:
    now = time.time()
    window = [t for t in _hits[key] if now - t < 60]
    if len(window) >= per_minute:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")
    window.append(now)
    _hits[key] = window


@app.on_event("startup")
async def _startup() -> None:
    db.init_db()
    app.state.redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))


def current_user(session: str | None = Cookie(default=None)) -> int:
    uid = auth.read_session(session) if session else None
    if uid is None or db.get_user(uid) is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return uid


def _set_session_cookie(resp: Response, uid: int) -> None:
    resp.set_cookie(
        "session", auth.make_session(uid),
        max_age=auth.SESSION_MAX_AGE, httponly=True, secure=True,
        samesite="strict", path="/",
    )


# ------------------------------ auth ------------------------------ #

@app.get("/api/me")
def me(uid: int = Depends(current_user)) -> dict:
    user = db.get_user(uid)
    return {"email": user["email"]}


@app.post("/api/signup")
def signup(body: SignupRequest, request: Request) -> JSONResponse:
    _rate_limit(f"signup:{request.client.host}", settings.rate_limit_login)
    if not auth.password_is_strong(body.password):
        raise HTTPException(
            status_code=400,
            detail="Use at least 10 characters with a mix of letters and numbers.",
        )
    if db.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="That email is already registered.")
    uid = db.create_user(body.email, auth.hash_password(body.password))
    resp = JSONResponse({"ok": True})
    _set_session_cookie(resp, uid)
    return resp


@app.post("/api/login")
def login(body: LoginRequest, request: Request) -> JSONResponse:
    _rate_limit(f"login:{request.client.host}", settings.rate_limit_login)
    uid = auth.authenticate(body.email, body.password, body.totp_code)
    if uid is None:
        raise HTTPException(status_code=401, detail="Incorrect email, password, or code.")
    resp = JSONResponse({"ok": True})
    _set_session_cookie(resp, uid)
    return resp


@app.post("/api/logout")
def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session", path="/")
    return resp


# ------------------------------ jobs ------------------------------ #

@app.post("/api/jobs")
async def submit_job(body: JobRequest, request: Request, uid: int = Depends(current_user)) -> dict:
    _rate_limit(f"submit:{request.client.host}", settings.rate_limit_submit)
    from .security import UnsafeURLError, validate_url

    try:
        url = validate_url(body.url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = uuid.uuid4().hex
    db.record_job(job_id, uid, url, body.mode)
    await app.state.redis.enqueue_job("download", job_id, url, body.mode, uid, _job_id=job_id)
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs(uid: int = Depends(current_user)) -> list[dict]:
    return db.list_jobs(uid)


@app.get("/api/jobs/{job_id}/progress")
async def job_progress(job_id: str, uid: int = Depends(current_user)) -> dict:
    job = db.get_job(job_id)
    if not job or job["user_id"] != uid:
        raise HTTPException(status_code=404, detail="Not found.")
    raw = await app.state.redis.get(f"progress:{job_id}")
    return json.loads(raw) if raw else {"status": "queued", "progress": 0}


@app.websocket("/api/ws/{job_id}")
async def job_ws(ws: WebSocket, job_id: str) -> None:
    uid = auth.read_session(ws.cookies.get("session", ""))
    job = db.get_job(job_id)
    if uid is None or not job or job["user_id"] != uid:
        await ws.close(code=4401)
        return
    await ws.accept()
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        while True:
            raw = await redis.get(f"progress:{job_id}")
            payload = json.loads(raw) if raw else {"status": "queued", "progress": 0}
            await ws.send_json(payload)
            if payload.get("status") in {"done", "error"}:
                break
            await asyncio.sleep(1)
    finally:
        await redis.close()
        await ws.close()


@app.get("/api/files/{job_id}")
def download_file(job_id: str, uid: int = Depends(current_user)) -> FileResponse:
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid file id.")
    job = db.get_job(job_id)
    if not job or job["user_id"] != uid:
        raise HTTPException(status_code=404, detail="File not found or expired.")
    job_dir = Path(settings.download_dir) / job_id
    files = list(job_dir.iterdir()) if job_dir.is_dir() else []
    if not files:
        raise HTTPException(status_code=404, detail="File not found or expired.")
    f = files[0]

    def _purge_after_send() -> None:
        # The user now has the file on their PC — remove it from the server.
        shutil.rmtree(job_dir, ignore_errors=True)
        db.update_job(job_id, status="removed", filename=None)

    return FileResponse(
        f, filename=f.name, media_type="application/octet-stream",
        background=BackgroundTask(_purge_after_send),
    )


@app.get("/api/youtube/status")
def youtube_status(uid: int = Depends(current_user)) -> dict:
    f = Path(settings.user_cookies_dir) / str(uid) / "cookies.txt"
    return {"connected": f.is_file()}


@app.post("/api/youtube/cookies")
async def upload_cookies(file: UploadFile = File(...), uid: int = Depends(current_user)) -> dict:
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="That file is too large to be a cookies file.")
    text = data.decode("utf-8", errors="replace")
    looks_ok = ("netscape" in text.lower()) or ("\t" in text) or ("youtube" in text.lower())
    if not looks_ok:
        raise HTTPException(
            status_code=400,
            detail="That doesn't look like a cookies.txt. Export it in Netscape format and try again.",
        )
    try:
        user_dir = Path(settings.user_cookies_dir) / str(uid)
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "cookies.txt").write_text(text, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not save cookies: {exc}") from exc
    return {"connected": True}


@app.delete("/api/youtube/cookies")
def disconnect_youtube(uid: int = Depends(current_user)) -> dict:
    f = Path(settings.user_cookies_dir) / str(uid) / "cookies.txt"
    f.unlink(missing_ok=True)
    return {"connected": False}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
