"""Authentication: Argon2id hashing, optional TOTP MFA, signed sessions.

Multi-tenant: each user has an email + password. Secure defaults (CISA):
no shipped password, strong hashing, MFA available free.
"""
from __future__ import annotations

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import db
from .config import settings

_ph = PasswordHasher()
_serializer = URLSafeTimedSerializer(settings.session_secret, salt="videodead-session")

SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
MIN_PASSWORD_LEN = 10


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False


def password_is_strong(password: str) -> bool:
    """Minimal strength gate: length plus a little variety."""
    if len(password) < MIN_PASSWORD_LEN:
        return False
    classes = sum(
        bool(any(c in group for c in password))
        for group in ("abcdefghijklmnopqrstuvwxyz",
                      "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                      "0123456789",
                      "!@#$%^&*()-_=+[]{};:,.<>/?")
    )
    return classes >= 2


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def make_session(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session(token: str) -> int | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return int(data["uid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None


def authenticate(email: str, password: str, totp_code: str | None) -> int | None:
    """Return the user id on success, else None."""
    user = db.get_user_by_email(email)
    if not user or not verify_password(user["password_hash"], password):
        return None
    if user["totp_secret"]:
        if not totp_code or not verify_totp(user["totp_secret"], totp_code):
            return None
    return int(user["id"])
