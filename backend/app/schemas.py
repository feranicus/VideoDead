"""Request/response models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    totp_code: str | None = Field(default=None, max_length=8)


class JobRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    mode: Literal["video", "audio"] = "video"


class JobView(BaseModel):
    id: str
    url: str
    mode: str
    status: str
    filename: str | None = None
    error: str | None = None
    progress: float = 0.0
