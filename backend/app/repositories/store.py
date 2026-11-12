"""Database queries used by services."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    AgentDevice,
    AuditLog,
    ComplianceState,
    Course,
    Enrollment,
    Environment,
    EnvironmentRevision,
    InstallationJob,
    JobEvent,
    Notification,
    PairingCode,
    RefreshToken,
    SoftwareRequirement,
    User,
    VerificationResult,
)


def user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def user_by_google_sub(db: Session, sub: str) -> User | None:
    return db.scalar(select(User).where(User.google_sub == sub))


def refresh_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))


def course_by_id(db: Session, course_id: uuid.UUID) -> Course | None:
    return db.get(Course, course_id)


def active_enrollment(db: Session, student_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment | None:
    return db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status == "active",
        )
    )


def environment_by_id(db: Session, environment_id: uuid.UUID) -> Environment | None:
    return db.get(Environment, environment_id)


def revision_by_id(db: Session, revision_id: uuid.UUID) -> EnvironmentRevision | None:
    return db.get(EnvironmentRevision, revision_id)


def requirements_for(db: Session, revision_id: uuid.UUID) -> list[SoftwareRequirement]:
    return list(
        db.scalars(
            select(SoftwareRequirement)
            .where(SoftwareRequirement.revision_id == revision_id)
            .order_by(SoftwareRequirement.display_name)
        )
    )


def latest_revision_number(db: Session, environment_id: uuid.UUID) -> int:
    value = db.scalar(
        select(func.max(EnvironmentRevision.revision_number)).where(
            EnvironmentRevision.environment_id == environment_id
        )
    )
    return int(value or 0)


def device_by_id(db: Session, device_id: uuid.UUID) -> AgentDevice | None:
    return db.get(AgentDevice, device_id)


def active_device_for_student(db: Session, student_id: uuid.UUID) -> AgentDevice | None:
    return db.scalar(
        select(AgentDevice).where(AgentDevice.student_id == student_id, AgentDevice.status == "active")
    )


def pairing_by_hash(db: Session, code_hash: str) -> PairingCode | None:
    return db.scalar(select(PairingCode).where(PairingCode.code_hash == code_hash))


def job_by_id(db: Session, job_id: uuid.UUID) -> InstallationJob | None:
    return db.get(InstallationJob, job_id)


def job_by_idempotency(db: Session, key: str) -> InstallationJob | None:
    return db.scalar(select(InstallationJob).where(InstallationJob.idempotency_key == key))


def active_job(
    db: Session,
    student_id: uuid.UUID,
    device_id: uuid.UUID,
    revision_id: uuid.UUID,
    operation: str,
) -> InstallationJob | None:
    return db.scalar(
        select(InstallationJob).where(
            InstallationJob.student_id == student_id,
            InstallationJob.device_id == device_id,
            InstallationJob.revision_id == revision_id,
            InstallationJob.operation == operation,
            InstallationJob.status.in_(
                ["pending", "planning", "awaiting_approval", "installing", "verifying"]
            ),
        )
    )


def next_agent_job(db: Session, device_id: uuid.UUID) -> InstallationJob | None:
    return db.scalar(
        select(InstallationJob)
        .where(
            InstallationJob.device_id == device_id,
            InstallationJob.status.in_(
                ["pending", "planning", "awaiting_approval", "installing", "verifying"]
            ),
        )
        .order_by(InstallationJob.created_at)
    )


def compliance_for(
    db: Session, student_id: uuid.UUID, environment_id: uuid.UUID
) -> ComplianceState | None:
    return db.scalar(
        select(ComplianceState).where(
            ComplianceState.student_id == student_id,
            ComplianceState.environment_id == environment_id,
        )
    )


def paginate(db: Session, query: Select, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)))
    return items, int(total or 0)


def job_events(db: Session, job_id: uuid.UUID) -> list[JobEvent]:
    return list(db.scalars(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)))


def verification_results(db: Session, job_id: uuid.UUID) -> list[VerificationResult]:
    return list(
        db.scalars(select(VerificationResult).where(VerificationResult.job_id == job_id).order_by(VerificationResult.tool))
    )


def notifications_for(db: Session, user_id: uuid.UUID) -> Select:
    return select(Notification).where(Notification.recipient_id == user_id).order_by(Notification.created_at.desc())


def audit_query() -> Select:
    return select(AuditLog).order_by(AuditLog.created_at.desc())
