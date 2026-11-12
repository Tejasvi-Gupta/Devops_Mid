"""Shared service helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.sanitize import redact
from app.models import AuditLog, Notification


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp_page(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def audit(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: str,
    outcome: str,
    context: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            context=redact(context or {}),
        )
    )


def notify(db: Session, recipient_id: uuid.UUID, type_: str, payload: dict) -> None:
    db.add(Notification(recipient_id=recipient_id, type=type_, payload=redact(payload)))
