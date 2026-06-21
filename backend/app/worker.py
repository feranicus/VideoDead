"""arq worker: pulls jobs from Redis and runs yt-dlp as a library.

yt-dlp is invoked with a fixed options dict — user input only ever populates the
URL and the mode, never a shell string. Progress is pushed to Redis so the API
can stream it over WebSocket.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile

import json
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from yt_dlp import YoutubeDL

from . import db
from .config import settings
from .security import UnsafeURLError, validate_url

_PROGRESS_KEY = "progress:{job_id}"


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


def _ydl_options(job_id: str, hook) -> dict:
    """Fixed, safe yt-dlp options. No user-controlled flags."""
    outtmpl = str(Path(settings.download_dir) / job_id / "%(title).80s.%(ext)s")
    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "restrictfilenames": True,
        "max_filesize": settings.max_filesize_bytes,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        # yt-dlp refuses DRM-protected streams; we do not add any bypass.
        "nocheckcertificate": False,
    }
    return opts


async def download(ctx, job_id: str, url: str, mode: str) -> None:
    redis = ctx["redis"]

    async def publish(payload: dict) -> None:
        await redis.set(_PROGRESS_KEY.format(job_id=job_id), json.dumps(payload), ex=3600)

    try:
        validate_url(url)  # re-validate at execution time (defence in depth)
    except UnsafeURLError as exc:
        db.update_job(job_id, status="error", error=str(exc))
        await publish({"status": "error", "error": str(exc), "progress": 0})
        return

    state = {"progress": 0.0, "filename": None}

    def hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            if total:
                state["progress"] = round(done / total * 100, 1)
        elif d.get("status") == "finished":
            state["filename"] = d.get("filename")

    opts = _ydl_options(job_id, hook)
    if mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = "bestvideo*+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    # yt-dlp rewrites the cookies file after use, so copy the (read-only) source
    # to a writable temp file and hand that to yt-dlp. Fully automatic.
    cookie_tmp = None
    src = Path(settings.cookies_file)
    if src.is_file():
        fd, cookie_tmp = tempfile.mkstemp(prefix="ck_", suffix=".txt")
        os.close(fd)
        shutil.copyfile(src, cookie_tmp)
        opts["cookiefile"] = cookie_tmp

    db.update_job(job_id, status="downloading")
    await publish({"status": "downloading", "progress": 0})

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        # Log the full reason for operators...
        logging.getLogger("videodead").exception("Download failed for %s", url)
        reason = str(exc).strip().splitlines()[-1] if str(exc).strip() else exc.__class__.__name__
        low = reason.lower()
        if "sign in to confirm" in low or "bot" in low:
            msg = "This site is blocking the server. For YouTube, add a cookies file (see docs/YOUTUBE_COOKIES.md)."
        elif "drm" in low or "protected" in low:
            msg = "That video is DRM-protected and cannot be downloaded."
        elif "requested format" in low:
            msg = "No downloadable format was found for that link."
        else:
            msg = "We couldn't download that link. Reason: " + reason[:200]
        db.update_job(job_id, status="error", error=msg)
        await publish({"status": "error", "error": msg, "progress": 0})
        return
    finally:
        if cookie_tmp:
            Path(cookie_tmp).unlink(missing_ok=True)

    fname = None
    job_dir = Path(settings.download_dir) / job_id
    if job_dir.is_dir():
        files = sorted(job_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            fname = files[0].name

    db.update_job(job_id, status="done", filename=fname)
    await publish({"status": "done", "progress": 100, "filename": fname})


async def purge_old_files(ctx) -> None:
    """Delete finished downloads older than the TTL (privacy by default)."""
    import time

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
