"""Administrator controls."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found, validation_error
from app.models import User
from app.repositories.store import audit_query, paginate
from app.services.common import audit, clamp_page


def list_users(db: Session, page: int, page_size: int) -> tuple[list[User], int]:
    page, page_size = clamp_page(page, page_size)
    return paginate(db, select(User).order_by(User.created_at.desc()), page, page_size)


def set_instructor(db: Session, actor: User, user_id: uuid.UUID, approved: bool) -> User:
    user = db.get(User, user_id)
    if not user:
        raise not_found("User not found")
    if approved:
        user.role = "instructor"
        user.instructor_status = "approved"
        action = "instructor.approve"
    else:
        user.role = "student"
        user.instructor_status = "rejected"
        action = "instructor.reject"
    audit(db, actor_id=actor.id, action=action, target_type="user", target_id=str(user.id), outcome="success")
    db.commit()
    db.refresh(user)
    return user


def set_account(db: Session, actor: User, user_id: uuid.UUID, active: bool) -> User:
    user = db.get(User, user_id)
    if not user:
        raise not_found("User not found")
    if user.id == actor.id and not active:
        raise validation_error("You cannot suspend your own account")
    user.account_status = "active" if active else "suspended"
    audit(
        db,
        actor_id=actor.id,
        action="user.reactivate" if active else "user.suspend",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
    )
    db.commit()
    db.refresh(user)
    return user


def set_role(db: Session, actor: User, user_id: uuid.UUID, role: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise not_found("User not found")
    if user.id == actor.id and role != "admin":
        raise validation_error("You cannot remove your own administrator access")
    user.role = role
    if role == "instructor":
        user.instructor_status = "approved"
    elif role == "student":
        user.instructor_status = "not_applicable"
    elif role == "admin":
        user.instructor_status = "not_applicable"
    audit(
        db,
        actor_id=actor.id,
        action="user.role_change",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        context={"role": role},
    )
    db.commit()
    db.refresh(user)
    return user


def list_audit(db: Session, page: int, page_size: int):
    page, page_size = clamp_page(page, page_size)
    return paginate(db, audit_query(), page, page_size)
