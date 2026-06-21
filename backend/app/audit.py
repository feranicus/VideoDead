"""Structured audit logging — the security 'black box' of VideoDead.

Every meaningful action writes ONE line of JSON to stdout. Promtail ships those
lines to Loki, and Grafana surfaces them in real time (who connected, when, from
which IP/device, which links they submitted, which files they saved) plus alerts
on suspicious activity.

IMPORTANT: passwords are NEVER logged. They are one-way hashed (Argon2id) and
surfacing them would break the whole security model. We log *who/when/where/what*
and authentication outcomes (including failures), which is what actually exposes
abuse — not the secret itself.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

# ----- dedicated stdout logger that emits the raw JSON line, nothing else ----- #
_log = logging.getLogger("videodead.audit")
if not _log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(message)s"))
    _log.addHandler(_h)
    _log.setLevel(logging.INFO)
    _log.propagate = False  # don't let uvicorn duplicate/reformat it


# ------------------------------- request helpers ------------------------------ #

def client_ip(request) -> str:
    """Real client IP. Caddy sets X-Forwarded-For; take the first hop."""
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "?"
    except Exception:  # noqa: BLE001 - logging must never break a request
        return "?"


def client_ua(request) -> str:
    try:
        return (request.headers.get("user-agent") or "")[:300]
    except Exception:  # noqa: BLE001
        return ""


def device(ua: str) -> str:
    """KISS browser / OS label from a User-Agent string (no dependency)."""
    u = (ua or "").lower()
    browser = (
        "Edge" if "edg" in u else
        "Opera" if "opr" in u or "opera" in u else
        "Chrome" if "chrome" in u or "crios" in u else
        "Firefox" if "firefox" in u or "fxios" in u else
        "Safari" if "safari" in u else
        "Bot/Other"
    )
    osname = (
        "Windows" if "windows" in u else
        "Android" if "android" in u else
        "iOS" if "iphone" in u or "ipad" in u else
        "macOS" if "mac os" in u or "macintosh" in u else
        "Linux" if "linux" in u else
        "Other"
    )
    return f"{browser} / {osname}"


# ----------------------------- suspicious screening --------------------------- #
# Heuristic, NON-blocking watchlist. We FLAG (and alert) — we do not block yet.
# Strict AI guardrails come later. Extend at runtime with the env var
# SUSPICIOUS_DOMAINS="foo.com,bar.net".
_DEFAULT_SUSPICIOUS = [
    # torrent / piracy indexers
    "thepiratebay", "1337x", "rarbg", "nyaa", "yts.", "limetorrents",
    "torrentz", "kickass", "magnet:",
    # pirate streaming / ripping
    "fmovies", "putlocker", "123movies", "soap2day", "primewire",
    "sflix", "gomovies", "couchtuner", "watchseries", "yesmovies",
    # account/credential sharing dumps
    "pastebin.com/raw",
]
_EXTRA = [d.strip().lower() for d in os.getenv("SUSPICIOUS_DOMAINS", "").split(",") if d.strip()]
SUSPICIOUS_PATTERNS = _DEFAULT_SUSPICIOUS + _EXTRA


def screen_url(url: str) -> str | None:
    """Return the matched suspicious token, or None if the link looks ordinary."""
    if not url:
        return None
    hay = url.lower()
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        host = ""
    for token in SUSPICIOUS_PATTERNS:
        if token in host or token in hay:
            return token
    return None


# --------------------------------- the emitter -------------------------------- #

def audit(event: str, **fields) -> None:
    """Write one structured audit line. Drops any 'password'-like field defensively."""
    rec = {
        "log_type": "audit",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "epoch": int(time.time()),
        "event": event,
    }
    for k, v in fields.items():
        if v is None:
            continue
        if "password" in k.lower() or "secret" in k.lower() or "token" in k.lower():
            continue  # never, ever
        rec[k] = v
    try:
        _log.info(json.dumps(rec, ensure_ascii=False))
    except Exception:  # noqa: BLE001 - auditing must never crash the app
        pass
