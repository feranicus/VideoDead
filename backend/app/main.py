"""FastAPI app: first-run setup, login/MFA, job submit, progress, file download.

The web tier never downloads anything itself — it validates input and enqueues a
job onto Redis. Long work happens in the arq worker.
"""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.responses import FileResponse, JSONResponse

from . import auth, db
from .config import settings
from .schemas import JobRequest, LoginRequest, SetupRequest

app = FastAPI(title="VideoDead", version="1.0.0", docs_url=None, redoc_url=None)

# --- naive in-memory rate limiter (single instance is fine for one operator) ---
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


# ------------------------------ auth helpers ------------------------------ #

def current_user(session: str | None = Cookie(default=None)) -> int:
    uid = auth.read_session(session) if session else None
    if uid is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return uid


def _set_session_cookie(resp: Response, uid: int) -> None:
    resp.set_cookie(
        "session",
        auth.make_session(uid),
        max_age=auth.SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )


# ------------------------------ setup / auth ------------------------------ #

@app.get("/api/state")
def app_state() -> dict:
    """Tells the UI whether first-run setup is needed."""
    return {"needs_setup": not db.admin_exists()}


@app.post("/api/setup")
def setup(body: SetupRequest) -> JSONResponse:
    if db.admin_exists():
        raise HTTPException(status_code=409, detail="Already set up.")
    if not auth.password_is_strong(body.password):
        raise HTTPException(
            status_code=400,
            detail="Use at least 12 characters with a mix of letters, numbers and symbols.",
        )
    db.create_admin(settings.admin_email, auth.hash_password(body.password))
    return JSONResponse({"ok": True})


@app.post("/api/login")
def login(body: LoginRequest, request: Request) -> JSONResponse:
    _rate_limit(f"login:{request.client.host}", settings.rate_limit_login)
    uid = auth.authenticate(body.password, body.totp_code)
    if uid is None:
        raise HTTPException(status_code=401, detail="Incorrect password or code.")
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
    db.record_job(job_id, url, body.mode)
    await app.state.redis.enqueue_job("download", job_id, url, body.mode, _job_id=job_id)
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs")
def list_jobs(uid: int = Depends(current_user)) -> list[dict]:
    return db.list_jobs()


@app.get("/api/jobs/{job_id}/progress")
async def job_progress(job_id: str, uid: int = Depends(current_user)) -> dict:
    raw = await app.state.redis.get(f"progress:{job_id}")
    return json.loads(raw) if raw else {"status": "queued", "progress": 0}


@app.websocket("/api/ws/{job_id}")
async def job_ws(ws: WebSocket, job_id: str) -> None:
    # Cookie auth on the WS handshake.
    if auth.read_session(ws.cookies.get("session", "")) is None:
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
            import asyncio

            await asyncio.sleep(1)
    finally:
        await redis.close()
        await ws.close()


@app.get("/api/files/{job_id}")
def download_file(job_id: str, uid: int = Depends(current_user)) -> FileResponse:
    # job_id is a server-generated hex string; reject anything else (path-traversal guard).
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid file id.")
    job_dir = Path(settings.download_dir) / job_id
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="File not found or expired.")
    files = list(job_dir.iterdir())
    if not files:
        raise HTTPException(status_code=404, detail="File not found or expired.")
    f = files[0]
    return FileResponse(f, filename=f.name, media_type="application/octet-stream")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
