"""Password hashing, tokens, and cookie helpers."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response

from app.core.config import Settings

_hasher = PasswordHasher()
REFRESH_COOKIE = "epp_refresh"
CSRF_COOKIE = "epp_csrf"
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_secret(prefix: str = "") -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def new_pairing_code() -> str:
    raw = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def normalize_pairing_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def create_access_token(settings: Settings, user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])


def set_session_cookies(response: Response, settings: Settings, refresh_token: str, csrf_token: str) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    common = {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": max_age,
    }
    response.set_cookie(REFRESH_COOKIE, refresh_token, httponly=True, path="/api/v1/auth", **common)
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, path="/", **common)


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")
