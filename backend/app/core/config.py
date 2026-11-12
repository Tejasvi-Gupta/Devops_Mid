"""Application configuration loaded from the environment."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
PLACEHOLDER_SECRET = "replace-with-a-random-string-of-at-least-32-characters"


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = ""
    database_url: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    google_client_id: str = ""
    google_client_secret: str = ""
    agent_pairing_code_ttl_seconds: int = 300
    log_level: str = "INFO"
    aws_region: str = ""
    catalog_path: str = ""
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Platform Admin"
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 600
    pairing_rate_limit: int = 5
    pairing_rate_window_seconds: int = 600
    job_stale_seconds: int = 600
    max_job_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cookie_samesite")
    @classmethod
    def _samesite(cls, value: str) -> str:
        allowed = {"lax", "strict", "none"}
        lowered = value.lower()
        if lowered not in allowed:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return lowered


def find_catalog_path(settings: Settings) -> Path:
    if settings.catalog_path:
        return Path(settings.catalog_path)
    candidates = [
        REPO_ROOT / "catalog" / "tools.json",
        Path(__file__).resolve().parents[2] / "catalog" / "tools.json",
        Path("/app/catalog/tools.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_settings(settings: Settings) -> None:
    errors: list[str] = []
    if settings.app_env not in {"development", "test", "production"}:
        errors.append("APP_ENV must be development, test, or production")
    if len(settings.app_secret_key) < 32 or settings.app_secret_key == PLACEHOLDER_SECRET:
        errors.append("APP_SECRET_KEY must be a non-placeholder value of at least 32 characters")
    if not settings.database_url.startswith("postgresql"):
        errors.append("DATABASE_URL must be a PostgreSQL URL")
    if settings.access_token_expire_minutes < 1:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
    if settings.refresh_token_expire_days < 1:
        errors.append("REFRESH_TOKEN_EXPIRE_DAYS must be positive")
    if settings.agent_pairing_code_ttl_seconds < 30:
        errors.append("AGENT_PAIRING_CODE_TTL_SECONDS must be at least 30")
    if settings.cookie_samesite == "none" and not settings.cookie_secure:
        errors.append("COOKIE_SECURE must be true when COOKIE_SAMESITE is none")
    if settings.app_env == "production" and not settings.cookie_secure:
        errors.append("COOKIE_SECURE must be true in production")
    if errors:
        raise RuntimeError("Invalid configuration: " + "; ".join(errors))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if os.getenv("EPP_SKIP_CONFIG_VALIDATION") != "1":
        validate_settings(settings)
    return settings
