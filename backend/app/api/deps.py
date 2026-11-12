"""Request dependencies."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import forbidden, unauthorized
from app.db.session import get_db
from app.models import AgentDevice, User
from app.services.auth_service import user_from_access_token
from app.services.device_service import device_from_credential

bearer = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> User:
    if not credentials:
        raise unauthorized()
    return user_from_access_token(db, settings, credentials.credentials)


def current_instructor(user: User = Depends(current_user)) -> User:
    if user.role != "instructor" or user.instructor_status != "approved":
        raise forbidden("Approved instructor access is required")
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise forbidden("Administrator access is required")
    return user


def current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> AgentDevice:
    if not credentials or credentials.credentials.count(".") == 2:
        raise unauthorized("A device credential is required")
    return device_from_credential(db, credentials.credentials)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
