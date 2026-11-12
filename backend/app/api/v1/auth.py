"""Authentication routes."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_user, settings_dep
from app.core.config import Settings
from app.core.rate_limit import rate_limiter
from app.core.security import CSRF_COOKIE, REFRESH_COOKIE, clear_session_cookies, set_session_cookies
from app.db.session import get_db
from app.models import User
from app.schemas.dto import GoogleIn, LoginIn, ProfileUpdate, RegisterIn, TokenOut, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
users = APIRouter(prefix="/users", tags=["users"])


def _token(response: Response, settings: Settings, user, access: str, refresh: str, csrf: str) -> TokenOut:
    set_session_cookies(response, settings, refresh, csrf)
    return TokenOut(
        access_token=access,
        expires_in=settings.access_token_expire_minutes * 60,
        csrf_token=csrf,
        user=UserPublic.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    rate_limiter.check(f"register:{client_ip(request)}", settings.auth_rate_limit, settings.auth_rate_window_seconds)
    user, access, refresh, csrf = auth_service.register(
        db, settings, payload.name, payload.email, payload.password, payload.requested_role
    )
    return _token(response, settings, user, access, refresh, csrf)


@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    rate_limiter.check(f"login:{client_ip(request)}", settings.auth_rate_limit, settings.auth_rate_window_seconds)
    user, access, refresh, csrf = auth_service.login(db, settings, payload.email, payload.password)
    return _token(response, settings, user, access, refresh, csrf)


@router.post("/google", response_model=TokenOut)
def google(
    payload: GoogleIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    rate_limiter.check(f"google:{client_ip(request)}", settings.auth_rate_limit, settings.auth_rate_window_seconds)
    user, access, refresh, csrf = auth_service.google_sign_in(db, settings, payload.id_token, payload.requested_role)
    return _token(response, settings, user, access, refresh, csrf)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    header = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not header or header != cookie:
        from app.core.errors import unauthorized

        raise unauthorized("Session expired")
    user, access, refresh_token, csrf = auth_service.refresh_session(
        db, settings, request.cookies.get(REFRESH_COOKIE), header
    )
    return _token(response, settings, user, access, refresh_token, csrf)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth_service.logout(db, request.cookies.get(REFRESH_COOKIE))
    clear_session_cookies(response)


@router.get("/me", response_model=UserPublic)
@users.get("/me", response_model=UserPublic)
def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=UserPublic)
def update_me(payload: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = payload.name.strip()
    db.commit()
    db.refresh(user)
    return user
