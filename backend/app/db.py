"""Tiny SQLite layer: multiple user accounts + per-user job history.

One file, no ORM. Redis holds live queue state; this holds users and jobs.
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
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY,
                   email TEXT NOT NULL UNIQUE,
                   password_hash TEXT NOT NULL,
                   totp_secret TEXT,
                   created_at INTEGER NOT NULL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS jobs(
                   id TEXT PRIMARY KEY,
                   user_id INTEGER NOT NULL,
                   url TEXT NOT NULL,
                   mode TEXT NOT NULL,
                   status TEXT NOT NULL,
                   filename TEXT,
                   error TEXT,
                   created_at INTEGER NOT NULL)"""
        )


# ----------------------------- users ----------------------------- #

def user_count() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def create_user(email: str, password_hash: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO users(email, password_hash, created_at) VALUES(?,?,?)",
            (email.lower().strip(), password_hash, int(time.time())),
        )
        return int(cur.lastrowid)


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE email=?", (email.lower().strip(),)
        ).fetchone()


def get_user(user_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def set_totp_secret(user_id: int, secret: str | None) -> None:
    with _conn() as c:
        c.execute("UPDATE users SET totp_secret=? WHERE id=?", (secret, user_id))


# ----------------------------- jobs ------------------------------ #

def record_job(job_id: str, user_id: int, url: str, mode: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO jobs(id, user_id, url, mode, status, created_at) VALUES(?,?,?,?,?,?)",
            (job_id, user_id, url, mode, "queued", int(time.time())),
        )


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), job_id))


def get_job(job_id: str) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def list_jobs(user_id: int, limit: int = 25) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
