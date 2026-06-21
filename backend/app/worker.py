"""arq worker: pulls jobs from Redis and runs yt-dlp as a library.

yt-dlp is invoked with a fixed options dict - user input only ever populates the
URL and the mode, never a shell string. Live progress (phase, MB, speed) is
pushed to Redis from yt-dlp's hooks so the API can stream it over WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from yt_dlp import YoutubeDL

from . import db
from .audit import audit
from .config import settings
from .security import UnsafeURLError, validate_url

_PROGRESS_KEY = "progress:{job_id}"

# A small SYNC redis client, used only to publish progress from yt-dlp's
# (synchronous) hooks, which run in a worker thread off the event loop.
_sync_redis = None


def _sync_client():
    global _sync_redis
    if _sync_redis is None:
        import redis as _redis
        _sync_redis = _redis.Redis.from_url(settings.redis_url)
    return _sync_redis


def _email_for(user_id: int) -> str | None:
    try:
        u = db.get_user(user_id)
        return u["email"] if u else None
    except Exception:  # noqa: BLE001
        return None


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


def _ydl_options(job_id: str) -> dict:
    """Fixed, safe yt-dlp options. No user-controlled flags."""
    outtmpl = str(Path(settings.download_dir) / job_id / "%(title).70s_%(id)s.%(ext)s")
    return {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "restrictfilenames": True,
        "max_filesize": settings.max_filesize_bytes,
        "quiet": True,
        "no_warnings": True,
        # yt-dlp refuses DRM-protected streams; we do not add any bypass.
        "nocheckcertificate": False,
        # Try several YouTube player clients; some avoid the PO-token requirement.
        "extractor_args": {"youtube": {"player_client": ["tv", "web_safari", "web", "mweb"]}},
        # Allow yt-dlp to fetch the EJS challenge-solver so Deno can solve YouTube's "n".
        "remote_components": ["ejs:github"],
    }


async def download(ctx, job_id: str, url: str, mode: str, user_id: int = 0) -> None:
    redis = ctx["redis"]
    key = _PROGRESS_KEY.format(job_id=job_id)

    async def publish(payload: dict) -> None:
        await redis.set(key, json.dumps(payload), ex=3600)

    def publish_sync(payload: dict) -> None:
        try:
            _sync_client().set(key, json.dumps(payload), ex=3600)
        except Exception:  # noqa: BLE001 - progress must never crash a download
            pass

    try:
        validate_url(url)  # re-validate at execution time (defence in depth)
    except UnsafeURLError as exc:
        db.update_job(job_id, status="error", error=str(exc))
        await publish({"status": "error", "error": str(exc), "progress": 0})
        return

    state = {"filename": None}
    last = {"t": 0.0}
    t0 = time.time()

    def hook(d: dict) -> None:
        st = d.get("status")
        if st == "downloading":
            now = time.time()
            if now - last["t"] < 0.7:   # throttle redis writes
                return
            last["t"] = now
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            speed = d.get("speed")
            eta = d.get("eta")
            fi, fc = d.get("fragment_index"), d.get("fragment_count")
            if total:
                pct = round(done / total * 100, 1)
            elif fi and fc:
                pct = round(fi / fc * 100, 1)
            else:
                pct = None  # unknown total (live/HLS) -> indeterminate
            publish_sync({
                "status": "downloading",
                "phase": "downloading",
                "progress": pct,
                "downloaded_mb": round(done / 1048576, 1),
                "total_mb": round(total / 1048576, 1) if total else None,
                "speed_mbs": round(speed / 1048576, 2) if speed else None,
                "eta": eta,
            })
        elif st == "finished":
            state["filename"] = d.get("filename")
            publish_sync({"status": "downloading", "phase": "converting", "progress": 99})

    def pp_hook(d: dict) -> None:
        if d.get("status") == "started":
            publish_sync({"status": "downloading", "phase": "converting", "progress": 99})

    opts = _ydl_options(job_id)
    opts["progress_hooks"] = [hook]
    opts["postprocessor_hooks"] = [pp_hook]
    if mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = "bestvideo*+bestaudio/best/best"
        opts["merge_output_format"] = "mp4"

    # yt-dlp rewrites the cookies file after use, so copy the (read-only) source
    # to a writable temp file and hand that to yt-dlp. PER-USER cookies only.
    cookie_tmp = None
    candidates = (
        Path(f"{settings.user_cookies_dir}/{user_id}/cookies.txt"),
        Path(f"/cookies/{user_id}/cookies.txt"),
    )
    src = next((p for p in candidates if p.is_file()), None)
    if src is not None:
        fd, cookie_tmp = tempfile.mkstemp(prefix="ck_", suffix=".txt")
        os.close(fd)
        shutil.copyfile(src, cookie_tmp)
        opts["cookiefile"] = cookie_tmp

    db.update_job(job_id, status="downloading")
    # "preparing" = resolving the page / formats (can take a few seconds on some sites)
    await publish({"status": "downloading", "phase": "preparing", "progress": 0})

    def _run() -> None:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])

    try:
        # Run blocking yt-dlp off the event loop so progress + other jobs flow.
        await asyncio.to_thread(_run)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        logging.getLogger("videodead").exception("Download failed for %s", url)
        reason = str(exc).strip().splitlines()[-1] if str(exc).strip() else exc.__class__.__name__
        low = reason.lower()
        if "sign in to confirm" in low or "bot" in low:
            msg = "YouTube needs you to connect your own account first (Connect YouTube in the app)."
        elif "drm" in low or "protected" in low:
            msg = "That video is DRM-protected and cannot be downloaded."
        elif "unsupported url" in low:
            msg = ("This link isn't a supported video page. Open it, start the video, then copy "
                   "the address of the page where the video actually plays and paste that.")
        elif "requested format" in low:
            msg = "No downloadable format was found for that link."
        elif "private" in low or "members-only" in low or "login" in low or "log in" in low:
            msg = "That video is private or needs an account. Connect the relevant account and try again."
        else:
            msg = "We couldn't download that link. Reason: " + reason[:200]
        db.update_job(job_id, status="error", error=msg)
        audit("download.error", email=_email_for(user_id), uid=user_id, job_id=job_id,
              url=url, reason=msg[:300], seconds=round(time.time() - t0, 1))
        await publish({"status": "error", "error": msg, "progress": 0})
        return
    finally:
        if cookie_tmp:
            Path(cookie_tmp).unlink(missing_ok=True)

    fname, fbytes = None, 0
    job_dir = Path(settings.download_dir) / job_id
    if job_dir.is_dir():
        files = sorted(job_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            fname = files[0].name
            fbytes = files[0].stat().st_size

    db.update_job(job_id, status="done", filename=fname)
    audit("download.complete", email=_email_for(user_id), uid=user_id, job_id=job_id,
          url=url, filename=fname, bytes=fbytes, mode=mode, seconds=round(time.time() - t0, 1))
    await publish({"status": "done", "phase": "done", "progress": 100, "filename": fname})


async def purge_old_files(ctx) -> None:
    """Delete finished downloads older than the TTL (privacy by default)."""
    cutoff = time.time() - settings.file_ttl_hours * 3600
    root = Path(settings.download_dir)
    if not root.is_dir():
        return
    for job_dir in root.iterdir():
        if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
            for f in job_dir.iterdir():
                f.unlink(missing_ok=True)
            job_dir.rmdir()


async def startup(ctx) -> None:
    db.init_db()


class WorkerSettings:
    functions = [download]
    cron_jobs = [cron(purge_old_files, hour=set(range(0, 24)), minute={0})]
    on_startup = startup
    redis_settings = _redis_settings()
    max_jobs = settings.max_concurrent_downloads
    job_timeout = settings.job_timeout_seconds  # was 300s default -> large files were cancelled
