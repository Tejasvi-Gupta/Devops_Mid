"""Pairing codes and device credentials."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import conflict, forbidden, not_found, unauthorized
from app.core.security import new_pairing_code, new_secret, normalize_pairing_code, sha256_hex
from app.models import AgentDevice, User
from app.repositories.store import active_device_for_student, device_by_id, pairing_by_hash
from app.services.common import audit, notify, utcnow


def create_pairing_code(db: Session, settings: Settings, user: User, replace_existing: bool) -> str:
    if user.role != "student":
        raise forbidden("Only a student can pair a device")
    active = active_device_for_student(db, user.id)
    if active and not replace_existing:
        raise conflict("This account already has an active device. Replace it explicitly to pair a new one.")
    code = new_pairing_code()
    from app.models import PairingCode

    db.add(
        PairingCode(
            user_id=user.id,
            code_hash=sha256_hex(normalize_pairing_code(code)),
            expires_at=utcnow() + timedelta(seconds=settings.agent_pairing_code_ttl_seconds),
            replace_existing=replace_existing,
        )
    )
    audit(
        db,
        actor_id=user.id,
        action="device.pairing_code",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        context={"replace_existing": replace_existing},
    )
    db.commit()
    return code


def pair_device(db: Session, code: str, display_name: str, platform: str) -> tuple[AgentDevice, str]:
    row = pairing_by_hash(db, sha256_hex(normalize_pairing_code(code)))
    if not row or row.used_at is not None or row.expires_at < utcnow():
        raise unauthorized("Pairing code is invalid, expired, or already used")
    student = db.get(User, row.user_id)
    if not student or student.account_status != "active":
        raise unauthorized("Pairing code is invalid, expired, or already used")
    active = active_device_for_student(db, student.id)
    if active and not row.replace_existing:
        raise conflict("This account already has an active device")
    if active and row.replace_existing:
        active.status = "revoked"
        active.revoked_at = utcnow()
        db.flush()
    credential = new_secret("dvc_")
    device = AgentDevice(
        student_id=student.id,
        display_name=display_name.strip(),
        platform=platform,
        credential_hash=sha256_hex(credential),
        last_seen_at=utcnow(),
    )
    row.used_at = utcnow()
    db.add(device)
    db.flush()
    notify(db, student.id, "device_registered", {"device_id": str(device.id), "display_name": device.display_name})
    audit(
        db,
        actor_id=student.id,
        action="device.pair",
        target_type="agent_device",
        target_id=str(device.id),
        outcome="success",
    )
    db.commit()
    db.refresh(device)
    return device, credential


def list_devices(db: Session, user: User) -> list[AgentDevice]:
    if user.role == "admin":
        query = select(AgentDevice).order_by(AgentDevice.registered_at.desc())
    else:
        query = select(AgentDevice).where(AgentDevice.student_id == user.id).order_by(AgentDevice.registered_at.desc())
    return list(db.scalars(query))


def revoke_device(db: Session, user: User, device_id: uuid.UUID) -> AgentDevice:
    device = device_by_id(db, device_id)
    if not device:
        raise not_found("Device not found")
    if user.role != "admin" and device.student_id != user.id:
        raise forbidden("You cannot revoke this device")
    if device.status == "revoked":
        return device
    device.status = "revoked"
    device.revoked_at = utcnow()
    notify(db, device.student_id, "device_revoked", {"device_id": str(device.id)})
    audit(
        db,
        actor_id=user.id,
        action="device.revoke",
        target_type="agent_device",
        target_id=str(device.id),
        outcome="success",
    )
    db.commit()
    db.refresh(device)
    return device


def device_from_credential(db: Session, token: str) -> AgentDevice:
    device = db.scalar(select(AgentDevice).where(AgentDevice.credential_hash == sha256_hex(token)))
    if not device or device.status != "active":
        raise unauthorized("Device credential is invalid or revoked")
    student = db.get(User, device.student_id)
    if not student or student.account_status != "active":
        raise unauthorized("Device credential is invalid or revoked")
    device.last_seen_at = utcnow()
    db.commit()
    return device
