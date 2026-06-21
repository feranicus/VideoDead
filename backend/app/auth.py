"""Authentication: Argon2id password hashing, optional TOTP MFA, signed sessions.

Secure defaults (CISA): no shipped password, MFA available free, strong hashing.
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

SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours idle ceiling
MIN_PASSWORD_LEN = 12


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False


def password_is_strong(password: str) -> bool:
    """Minimal strength gate — length plus some variety. No upper bound trap."""
    if len(password) < MIN_PASSWORD_LEN:
        return False
    classes = sum(
        bool(any(c in group for c in password))
        for group in ("abcdefghijklmnopqrstuvwxyz",
                      "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                      "0123456789",
                      "!@#$%^&*()-_=+[]{};:,.<>/?")
    )
    return classes >= 3


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def make_session(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session(token: str) -> int | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return int(data["uid"])
    except (BadSignature, KeyError, ValueError):
        return None


def authenticate(password: str, totp_code: str | None) -> int | None:
    """Return the user id on success, else None."""
    admin = db.get_admin()
    if not admin or not verify_password(admin["password_hash"], password):
        return None
    if admin["totp_secret"]:
        if not totp_code or not verify_totp(admin["totp_secret"], totp_code):
            return None
    return int(admin["id"])
