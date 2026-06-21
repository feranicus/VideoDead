"""Tiny SQLite layer for the single admin user and job history.

Kept deliberately minimal — one file, no ORM. Redis holds live queue state.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .config import settings

_DB_PATH = Path(settings.data_dir) / "videodead.sqlite"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY,
                   email TEXT NOT NULL,
                   password_hash TEXT NOT NULL,
                   totp_secret TEXT,
                   created_at INTEGER NOT NULL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS jobs(
                   id TEXT PRIMARY KEY,
                   url TEXT NOT NULL,
                   mode TEXT NOT NULL,
                   status TEXT NOT NULL,
                   filename TEXT,
                   error TEXT,
                   created_at INTEGER NOT NULL)"""
        )


def admin_exists() -> bool:
    with _conn() as c:
        return c.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


def create_admin(email: str, password_hash: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO users(email, password_hash, created_at) VALUES(?,?,?)",
            (email, password_hash, int(time.time())),
        )


def get_admin() -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM users LIMIT 1").fetchone()


def set_totp_secret(user_id: int, secret: str | None) -> None:
    with _conn() as c:
        c.execute("UPDATE users SET totp_secret=? WHERE id=?", (secret, user_id))


def record_job(job_id: str, url: str, mode: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO jobs(id, url, mode, status, created_at) VALUES(?,?,?,?,?)",
            (job_id, url, mode, "queued", int(time.time())),
        )


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), job_id))


def list_jobs(limit: int = 25) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
