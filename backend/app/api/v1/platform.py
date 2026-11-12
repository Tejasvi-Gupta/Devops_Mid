"""Courses, environments, jobs, devices, and notifications."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import current_instructor, current_user, settings_dep
from app.core.config import Settings
from app.core.errors import not_found
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import Notification, User
from app.repositories.store import notifications_for, paginate
from app.schemas.dto import (
    ApproveIn,
    CourseIn,
    CourseOut,
    DetectionIn,
    DeviceOut,
    EnrollmentIn,
    EnrollmentOut,
    EnvironmentIn,
    EnvironmentOut,
    JobCreateIn,
    PairingIn,
    RequirementIn,
    RevisionOut,
)
from app.services import course_service, device_service, environment_service, job_service
from app.services.common import clamp_page, utcnow

router = APIRouter(tags=["platform"])


def _environment_out(environment, revisions) -> EnvironmentOut:
    return EnvironmentOut(
        id=environment.id,
        course_id=environment.course_id,
        name=environment.name,
        description=environment.description,
        current_published_revision_id=environment.current_published_revision_id,
        revisions=[
            RevisionOut(
                id=item.id,
                environment_id=item.environment_id,
                revision_number=item.revision_number,
                publication_status=item.publication_status,
                specification=item.specification,
                published_at=item.published_at,
            )
            for item in revisions
        ],
    )


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseIn, user: User = Depends(current_instructor), db: Session = Depends(get_db)):
    return course_service.create_course(db, user, payload.name, payload.description, payload.class_code)


@router.get("/courses", response_model=list[CourseOut])
def list_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return course_service.list_courses(db, user)


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return course_service.get_course(db, user, course_id)


@router.post("/courses/{course_id}/enrollments", response_model=EnrollmentOut, status_code=201)
def enroll(
    course_id: uuid.UUID,
    payload: EnrollmentIn,
    user: User = Depends(current_instructor),
    db: Session = Depends(get_db),
):
    return course_service.enroll(db, user, course_id, payload.email)


@router.get("/courses/{course_id}/enrollments")
def enrollments(course_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return course_service.list_enrollments(db, user, course_id)


@router.delete("/courses/{course_id}/enrollments/{enrollment_id}", status_code=204)
def remove_enrollment(
    course_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    user: User = Depends(current_instructor),
    db: Session = Depends(get_db),
):
    course_service.remove_enrollment(db, user, course_id, enrollment_id)


@router.get("/courses/{course_id}/readiness")
def readiness(course_id: uuid.UUID, user: User = Depends(current_instructor), db: Session = Depends(get_db)):
    return course_service.readiness(db, user, course_id)


@router.get("/courses/{course_id}/environments")
def course_environments(course_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        {"id": item.id, "name": item.name, "description": item.description, "course_id": item.course_id}
        for item in environment_service.list_for_course(db, user, course_id)
    ]


@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(
    payload: EnvironmentIn,
    user: User = Depends(current_instructor),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    environment = environment_service.create_environment(db, settings, user, payload.model_dump())
    environment, revisions = environment_service.get_environment(db, user, environment.id)
    return _environment_out(environment, revisions)


@router.get("/environments/{environment_id}", response_model=EnvironmentOut)
def get_environment(environment_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    environment, revisions = environment_service.get_environment(db, user, environment_id)
    return _environment_out(environment, revisions)


@router.post("/environments/{environment_id}/revisions", response_model=RevisionOut, status_code=201)
def new_revision(environment_id: uuid.UUID, user: User = Depends(current_instructor), db: Session = Depends(get_db)):
    revision = environment_service.new_draft(db, user, environment_id)
    return RevisionOut(
        id=revision.id,
        environment_id=revision.environment_id,
        revision_number=revision.revision_number,
        publication_status=revision.publication_status,
        specification=revision.specification,
        published_at=revision.published_at,
    )


@router.put("/revisions/{revision_id}", response_model=RevisionOut)
def update_revision(
    revision_id: uuid.UUID,
    payload: list[RequirementIn],
    user: User = Depends(current_instructor),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    revision = environment_service.update_draft(db, settings, user, revision_id, [item.model_dump() for item in payload])
    return RevisionOut(
        id=revision.id,
        environment_id=revision.environment_id,
        revision_number=revision.revision_number,
        publication_status=revision.publication_status,
        specification=revision.specification,
        published_at=revision.published_at,
    )


@router.post("/revisions/{revision_id}/publish", response_model=RevisionOut)
def publish(revision_id: uuid.UUID, user: User = Depends(current_instructor), db: Session = Depends(get_db)):
    revision = environment_service.publish(db, user, revision_id)
    return RevisionOut(
        id=revision.id,
        environment_id=revision.environment_id,
        revision_number=revision.revision_number,
        publication_status=revision.publication_status,
        specification=revision.specification,
        published_at=revision.published_at,
    )


@router.post("/environments/{environment_id}/plan")
def preview_plan(
    environment_id: uuid.UUID,
    payload: DetectionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    return job_service.preview_plan(db, settings, user, environment_id, payload.model_dump())


@router.post("/environments/{environment_id}/verify", status_code=201)
def verify_environment(
    environment_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    job = job_service.create_job(db, user, environment_id, str(uuid.uuid4()), "verify")
    return job_service.public_job(db, user, job)


@router.get("/student/environments")
def student_environments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return job_service.student_environments(db, user)


@router.post("/devices/pairing-codes")
def pairing_code(
    payload: PairingIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    rate_limiter.check(f"pair-code:{user.id}", settings.pairing_rate_limit, settings.pairing_rate_window_seconds)
    code = device_service.create_pairing_code(db, settings, user, payload.replace_existing)
    return {"pairing_code": code, "expires_in": settings.agent_pairing_code_ttl_seconds}


@router.get("/devices", response_model=list[DeviceOut])
def devices(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return device_service.list_devices(db, user)


@router.post("/devices/{device_id}/revoke", response_model=DeviceOut)
def revoke_device(device_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return device_service.revoke_device(db, user, device_id)


@router.post("/jobs", status_code=201)
def create_job(payload: JobCreateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = job_service.create_job(db, user, payload.environment_id, payload.idempotency_key, payload.operation)
    return job_service.public_job(db, user, job)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    job = job_service.get_job(db, settings, user, job_id)
    return job_service.public_job(db, user, job)


@router.get("/jobs/{job_id}/events")
def job_events(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return job_service.list_events(db, user, job_id)


@router.get("/jobs/{job_id}/verification")
def job_verification(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = job_service.verification_for(db, user, job_id)
    return [
        {
            "tool": row.tool,
            "required_constraint": row.required_constraint,
            "detected_version": row.detected_version,
            "outcome": row.outcome,
            "mandatory": row.mandatory,
            "details": row.details,
        }
        for row in rows
    ]


@router.post("/jobs/{job_id}/approve")
def approve(job_id: uuid.UUID, payload: ApproveIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = job_service.approve(db, user, job_id, payload.acknowledgements)
    return job_service.public_job(db, user, job)


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = job_service.cancel(db, user, job_id)
    return job_service.public_job(db, user, job)


@router.post("/jobs/{job_id}/retry", status_code=201)
def retry(
    job_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
    idempotency_key: str = Query(min_length=8, max_length=80),
):
    job = job_service.retry(db, settings, user, job_id, idempotency_key)
    return job_service.public_job(db, user, job)


@router.get("/notifications")
def notifications(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    page, page_size = clamp_page(page, page_size)
    items, total = paginate(db, notifications_for(db, user.id), page, page_size)
    return {
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "payload": item.payload,
                "read": item.read_at is not None,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(notification_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(Notification, notification_id)
    if not item or item.recipient_id != user.id:
        raise not_found("Notification not found")
    item.read_at = utcnow()
    db.commit()


@router.get("/catalog")
def catalog(user: User = Depends(current_user), settings: Settings = Depends(settings_dep)):
    del user
    from app.domain.catalog import get_catalog

    return get_catalog(settings).model_dump()
