"""Request/response models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, max_length=8)


class JobRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    mode: Literal["video", "audio"] = "video"
