"""Registration, sessions, and Google sign-in."""

from __future__ import annotations

import hmac
import uuid
from datetime import timedelta

import jwt
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, conflict, forbidden, unauthorized
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_secret,
    sha256_hex,
    verify_password,
)
from app.models import RefreshToken, User
from app.repositories.store import refresh_by_hash, user_by_email, user_by_google_sub
from app.services.common import audit, utcnow


def _session(db: Session, settings: Settings, user: User) -> tuple[str, str, str]:
    refresh = new_secret()
    csrf = new_secret()
    row = RefreshToken(
        user_id=user.id,
        token_hash=sha256_hex(refresh),
        csrf_hash=sha256_hex(csrf),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    db.flush()
    access = create_access_token(settings, user.id)
    return access, refresh, csrf


def register(db: Session, settings: Settings, name: str, email: str, password: str, requested_role: str):
    if user_by_email(db, email):
        raise conflict("An account with that email already exists")
    role = "instructor" if requested_role == "instructor" else "student"
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        instructor_status="pending" if role == "instructor" else "not_applicable",
    )
    db.add(user)
    db.flush()
    access, refresh, csrf = _session(db, settings, user)
    audit(
        db,
        actor_id=user.id,
        action="user.register",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        context={"role": role},
    )
    db.commit()
    db.refresh(user)
    return user, access, refresh, csrf


def login(db: Session, settings: Settings, email: str, password: str):
    user = user_by_email(db, email)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        audit(
            db,
            actor_id=user.id if user else None,
            action="user.login_failed",
            target_type="user",
            target_id=str(user.id) if user else "",
            outcome="failure",
            context={"email": email},
        )
        db.commit()
        raise unauthorized("Email or password is incorrect")
    if user.account_status != "active":
        raise forbidden("This account is suspended")
    access, refresh, csrf = _session(db, settings, user)
    audit(
        db,
        actor_id=user.id,
        action="user.login",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
    )
    db.commit()
    return user, access, refresh, csrf


def refresh_session(db: Session, settings: Settings, raw_refresh: str | None, csrf: str | None):
    if not raw_refresh or not csrf:
        raise unauthorized("Session expired")
    row = refresh_by_hash(db, sha256_hex(raw_refresh))
    if not row:
        raise unauthorized("Session expired")
    if row.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
        audit(
            db,
            actor_id=row.user_id,
            action="user.refresh_reuse",
            target_type="user",
            target_id=str(row.user_id),
            outcome="failure",
        )
        db.commit()
        raise unauthorized("Session expired")
    if row.expires_at < utcnow() or not hmac.compare_digest(row.csrf_hash, sha256_hex(csrf)):
        raise unauthorized("Session expired")
    user = db.get(User, row.user_id)
    if not user or user.account_status != "active":
        raise unauthorized("Session expired")
    row.revoked_at = utcnow()
    access, refresh, new_csrf = _session(db, settings, user)
    replacement = refresh_by_hash(db, sha256_hex(refresh))
    row.replaced_by_id = replacement.id if replacement else None
    db.commit()
    return user, access, refresh, new_csrf


def logout(db: Session, raw_refresh: str | None) -> None:
    if raw_refresh:
        row = refresh_by_hash(db, sha256_hex(raw_refresh))
        if row and row.revoked_at is None:
            row.revoked_at = utcnow()
            audit(
                db,
                actor_id=row.user_id,
                action="user.logout",
                target_type="user",
                target_id=str(row.user_id),
                outcome="success",
            )
    db.commit()


def user_from_access_token(db: Session, settings: Settings, token: str) -> User:
    try:
        payload = decode_access_token(settings, token)
    except jwt.PyJWTError as exc:
        raise unauthorized("Session expired") from exc
    if payload.get("typ") != "access":
        raise unauthorized("Session expired")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise unauthorized("Session expired") from exc
    user = db.get(User, user_id)
    if not user or user.account_status != "active":
        raise unauthorized("Session expired")
    return user


def google_sign_in(db: Session, settings: Settings, id_token_value: str, requested_role: str):
    if not settings.google_client_id:
        raise AppError("configuration_error", "Google sign-in is not configured", 503)
    info = _verify_google(id_token_value, settings.google_client_id)
    if not info.get("email_verified"):
        raise unauthorized("Google did not confirm this email address")
    email = str(info["email"]).lower()
    sub = str(info["sub"])
    user = user_by_google_sub(db, sub) or user_by_email(db, email)
    if user and user.google_sub and user.google_sub != sub:
        raise forbidden("This email is linked to a different Google account")
    if user and user.account_status != "active":
        raise forbidden("This account is suspended")
    if user and not user.google_sub:
        user.google_sub = sub
    if not user:
        role = "instructor" if requested_role == "instructor" else "student"
        user = User(
            name=str(info.get("name") or email.split("@")[0])[:200],
            email=email,
            google_sub=sub,
            role=role,
            instructor_status="pending" if role == "instructor" else "not_applicable",
        )
        db.add(user)
        db.flush()
    access, refresh, csrf = _session(db, settings, user)
    audit(
        db,
        actor_id=user.id,
        action="user.google_login",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
    )
    db.commit()
    db.refresh(user)
    return user, access, refresh, csrf


def _verify_google(token: str, client_id: str) -> dict:
    from google.auth.transport import requests
    from google.oauth2 import id_token

    try:
        return id_token.verify_oauth2_token(token, requests.Request(), client_id)
    except Exception as exc:
        raise unauthorized("Google sign-in could not be verified") from exc
