"""Administrator and health routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import current_admin, settings_dep
from app.core.config import Settings
from app.db.session import get_db
from app.models import User
from app.schemas.dto import RoleIn, UserPublic
from app.services import admin_service

router = APIRouter(tags=["admin"])


@router.get("/admin/users")
def users(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    del admin
    items, total = admin_service.list_users(db, page, page_size)
    return {
        "items": [UserPublic.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/admin/instructor-requests")
def instructor_requests(admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    del admin
    items, _total = admin_service.list_users(db, 1, 100)
    return [UserPublic.model_validate(item) for item in items if item.instructor_status == "pending"]


@router.post("/admin/instructors/{user_id}/approve", response_model=UserPublic)
def approve(user_id: uuid.UUID, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return admin_service.set_instructor(db, admin, user_id, True)


@router.post("/admin/instructors/{user_id}/reject", response_model=UserPublic)
def reject(user_id: uuid.UUID, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return admin_service.set_instructor(db, admin, user_id, False)


@router.post("/admin/users/{user_id}/suspend", response_model=UserPublic)
def suspend(user_id: uuid.UUID, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return admin_service.set_account(db, admin, user_id, False)


@router.post("/admin/users/{user_id}/reactivate", response_model=UserPublic)
def reactivate(user_id: uuid.UUID, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return admin_service.set_account(db, admin, user_id, True)


@router.post("/admin/users/{user_id}/role", response_model=UserPublic)
def role(user_id: uuid.UUID, payload: RoleIn, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    return admin_service.set_role(db, admin, user_id, payload.role)


@router.get("/admin/audit")
def audit_log(
    page: int = 1,
    page_size: int = 50,
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    del admin
    items, total = admin_service.list_audit(db, page, page_size)
    return {
        "items": [
            {
                "id": item.id,
                "actor_id": item.actor_id,
                "action": item.action,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "outcome": item.outcome,
                "context": item.context,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


health = APIRouter(tags=["health"])


@health.get("/health/live")
def live():
    return {"status": "live"}


@health.get("/health/ready")
def ready(db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    db.execute(text("SELECT 1"))
    return {"status": "ready", "environment": settings.app_env}
