"""Installation jobs, approval, verification, and readiness."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import conflict, forbidden, invalid_state, not_found, validation_error
from app.domain.catalog import get_catalog
from app.domain.planning import build_plan, detection_drift
from app.domain.sanitize import redact, strip_machine_details
from app.domain.state import TERMINAL_STATUSES, assert_transition, readiness_from_results
from app.domain.versions import VersionError, version_satisfies
from app.models import (
    AgentDevice,
    ComplianceState,
    Course,
    Enrollment,
    Environment,
    EnvironmentRevision,
    InstallationJob,
    JobEvent,
    User,
    VerificationResult,
)
from app.repositories.store import (
    active_device_for_student,
    active_enrollment,
    active_job,
    compliance_for,
    environment_by_id,
    job_by_id,
    job_by_idempotency,
    job_events,
    next_agent_job,
    verification_results,
)
from app.services.common import audit, notify, utcnow


def _move(job: InstallationJob, status: str) -> None:
    assert_transition(job.status, status)
    job.status = status
    job.updated_at = utcnow()
    if status in TERMINAL_STATUSES:
        job.finished_at = job.updated_at


def _event(db: Session, job: InstallationJob, event_type: str, message: str, **extra) -> None:
    db.add(
        JobEvent(
            job_id=job.id,
            event_type=event_type,
            message=message[:500],
            progress=extra.get("progress"),
            tool=extra.get("tool"),
            details=redact(extra.get("details") or {}),
        )
    )


def _requirements(revision: EnvironmentRevision) -> list[dict]:
    return list(revision.specification.get("requirements") or [])


def _published_revision(db: Session, environment: Environment) -> EnvironmentRevision:
    if not environment.current_published_revision_id:
        raise conflict("This environment has no published revision")
    revision = db.get(EnvironmentRevision, environment.current_published_revision_id)
    if not revision or revision.publication_status != "published":
        raise conflict("This environment has no published revision")
    return revision


def _set_compliance(db: Session, job: InstallationJob, environment_id: uuid.UUID, status: str, summary: dict) -> None:
    state = compliance_for(db, job.student_id, environment_id)
    if not state:
        state = ComplianceState(student_id=job.student_id, environment_id=environment_id)
        db.add(state)
    state.revision_id = job.revision_id
    state.job_id = job.id
    state.status = status
    state.summary = summary
    state.updated_at = utcnow()


def create_job(db: Session, user: User, environment_id: uuid.UUID, idempotency_key: str, operation: str):
    existing = job_by_idempotency(db, idempotency_key)
    if existing:
        if existing.student_id != user.id:
            raise conflict("Idempotency key is already in use")
        return existing
    if user.role != "student":
        raise forbidden("Only a student can start environment setup")
    environment = environment_by_id(db, environment_id)
    if not environment:
        raise not_found("Environment not found")
    if not active_enrollment(db, user.id, environment.course_id):
        raise forbidden("You are not enrolled in this course")
    revision = _published_revision(db, environment)
    device = active_device_for_student(db, user.id)
    if not device:
        raise conflict("Pair the Windows agent before starting setup")
    if active_job(db, user.id, device.id, revision.id, operation):
        raise conflict("An active job already exists for this environment")
    job = InstallationJob(
        student_id=user.id,
        device_id=device.id,
        revision_id=revision.id,
        operation=operation,
        idempotency_key=idempotency_key,
        approval_state="not_required" if operation == "verify" else "pending",
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise conflict("An active job already exists for this environment") from exc
    _event(db, job, "created", "Job created")
    _set_compliance(db, job, environment.id, "in_progress", {"operation": operation})
    db.commit()
    db.refresh(job)
    return job


def _load_authorized(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = job_by_id(db, job_id)
    if not job:
        raise not_found("Job not found")
    if user.role == "admin" or job.student_id == user.id:
        return job
    revision = db.get(EnvironmentRevision, job.revision_id)
    environment = environment_by_id(db, revision.environment_id) if revision else None
    course = db.get(Course, environment.course_id) if environment else None
    if course and course.instructor_id == user.id and user.instructor_status == "approved":
        return job
    raise forbidden("You cannot view this job")


def public_job(db: Session, user: User, job: InstallationJob) -> dict:
    owner = job.student_id == user.id
    detection = job.detection if owner else strip_machine_details(job.detection)
    plan = job.plan if owner else strip_machine_details(job.plan)
    revision = db.get(EnvironmentRevision, job.revision_id)
    return {
        "id": job.id,
        "student_id": job.student_id,
        "device_id": job.device_id,
        "revision_id": job.revision_id,
        "environment_id": revision.environment_id if revision else None,
        "operation": job.operation,
        "status": job.status,
        "approval_state": job.approval_state,
        "cancel_requested": job.cancel_requested,
        "error_summary": job.error_summary,
        "plan": plan,
        "detection": detection,
        "acknowledgements": job.acknowledgements or [],
        "retry_count": job.retry_count,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "finished_at": job.finished_at,
    }


def get_job(db: Session, settings: Settings, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = _load_authorized(db, user, job_id)
    _expire_if_stale(db, settings, job)
    return job


def list_events(db: Session, user: User, job_id: uuid.UUID) -> list[dict]:
    job = _load_authorized(db, user, job_id)
    owner = job.student_id == user.id
    events = []
    for event in job_events(db, job.id):
        details = event.details if owner else strip_machine_details(event.details)
        events.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "progress": event.progress,
                "tool": event.tool,
                "message": event.message,
                "details": details,
                "created_at": event.created_at,
            }
        )
    return events


def approve(db: Session, user: User, job_id: uuid.UUID, acknowledgements: list[str]) -> InstallationJob:
    job = _load_authorized(db, user, job_id)
    if job.student_id != user.id:
        raise forbidden("Only the student can approve this plan")
    if job.status != "awaiting_approval":
        raise invalid_state("This job is not waiting for approval")
    required = set((job.plan or {}).get("required_acknowledgements") or [])
    given = set(acknowledgements)
    missing = sorted(required - given)
    if missing:
        raise validation_error("Confirm every required acknowledgement", {"missing": missing})
    job.approval_state = "approved"
    job.acknowledgements = sorted(given)
    job.updated_at = utcnow()
    _event(db, job, "approval_recorded", "Student approved the installation plan")
    audit(
        db,
        actor_id=user.id,
        action="job.approve",
        target_type="installation_job",
        target_id=str(job.id),
        outcome="success",
    )
    db.commit()
    db.refresh(job)
    return job


def cancel(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = _load_authorized(db, user, job_id)
    if job.student_id != user.id and user.role != "admin":
        raise forbidden("You cannot cancel this job")
    if job.status in TERMINAL_STATUSES:
        raise invalid_state("This job has already finished")
    job.cancel_requested = True
    if job.status in {"pending", "planning", "awaiting_approval"}:
        _move(job, "cancelled")
        job.error_summary = "Cancelled before installation started."
        _event(db, job, "cancel_acknowledged", job.error_summary)
    else:
        _event(db, job, "cancel_requested", "Cancellation will take effect at the next safe checkpoint.")
    audit(
        db,
        actor_id=user.id,
        action="job.cancel",
        target_type="installation_job",
        target_id=str(job.id),
        outcome="success",
    )
    db.commit()
    db.refresh(job)
    return job


def retry(db: Session, settings: Settings, user: User, job_id: uuid.UUID, idempotency_key: str):
    job = _load_authorized(db, user, job_id)
    if job.student_id != user.id:
        raise forbidden("Only the student can retry this job")
    if job.status not in {"failed", "cancelled", "needs_attention"}:
        raise invalid_state("Only a failed, cancelled, or needs-attention job can be retried")
    if job.retry_count >= settings.max_job_retries:
        raise conflict("Retry limit reached")
    created = create_job(db, user, _environment_id(db, job), idempotency_key, job.operation)
    if created.retry_of_id is None and created.id != job.id:
        created.retry_of_id = job.id
        created.retry_count = job.retry_count + 1
        db.commit()
        db.refresh(created)
    return created


def _environment_id(db: Session, job: InstallationJob) -> uuid.UUID:
    revision = db.get(EnvironmentRevision, job.revision_id)
    if not revision:
        raise not_found("Revision not found")
    return revision.environment_id


def agent_work(db: Session, settings: Settings, device: AgentDevice) -> InstallationJob | None:
    job = next_agent_job(db, device.id)
    if job:
        _expire_if_stale(db, settings, job)
        if job.status in TERMINAL_STATUSES:
            return next_agent_job(db, device.id)
    return job


def claim(db: Session, device: AgentDevice, job_id: uuid.UUID) -> InstallationJob:
    job = _device_job(db, device, job_id)
    if job.status == "planning":
        return job
    if job.status != "pending":
        raise invalid_state("This job cannot be claimed")
    _move(job, "planning")
    job.started_at = utcnow()
    _event(db, job, "claimed", "Agent claimed the job")
    db.commit()
    db.refresh(job)
    return job


def submit_detection(db: Session, settings: Settings, device: AgentDevice, job_id: uuid.UUID, detection: dict):
    job = _device_job(db, device, job_id)
    if job.status == "pending":
        _move(job, "planning")
        job.started_at = job.started_at or utcnow()
    if job.status not in {"planning", "awaiting_approval"}:
        raise invalid_state("Detection is not accepted in the current state")
    if job.cancel_requested:
        _move(job, "cancelled")
        job.error_summary = "Cancelled before installation started."
        db.commit()
        return job
    revision = db.get(EnvironmentRevision, job.revision_id)
    previous = job.detection
    drifted = detection_drift(previous, detection)
    plan = build_plan(_requirements(revision), detection, get_catalog(settings))
    if job.operation == "verify":
        for action in plan["actions"]:
            if action["operation"] == "install":
                action["operation"] = "verify_only"
                action["approval_required"] = False
                action["reason"] = "Verification does not install software. " + action["reason"]
        plan["approval_required"] = False
        plan["required_acknowledgements"] = []
    job.detection = detection
    job.plan = plan
    target = "verifying" if job.operation == "verify" or not plan["approval_required"] else "awaiting_approval"
    if job.status != target:
        _move(job, target)
    if target == "awaiting_approval":
        if drifted or job.approval_state != "approved":
            job.approval_state = "pending"
            job.acknowledgements = []
    else:
        job.approval_state = "not_required"
    _event(db, job, "plan_ready", "Installation plan is ready")
    db.commit()
    db.refresh(job)
    return job


def start_install(db: Session, device: AgentDevice, job_id: uuid.UUID) -> InstallationJob:
    job = _device_job(db, device, job_id)
    if job.cancel_requested:
        if job.status not in TERMINAL_STATUSES:
            _move(job, "cancelled")
            job.error_summary = "Cancelled before the next installation step."
            db.commit()
        return job
    if job.status != "awaiting_approval" or job.approval_state != "approved":
        raise invalid_state("The student has not approved this plan")
    installs = [item for item in (job.plan or {}).get("actions", []) if item.get("operation") == "install"]
    if not installs:
        raise invalid_state("This plan has no install step")
    _move(job, "installing")
    _event(db, job, "execution_started", "Agent started the approved install steps")
    db.commit()
    db.refresh(job)
    return job


def agent_event(db: Session, device: AgentDevice, job_id: uuid.UUID, payload: dict) -> InstallationJob:
    job = _device_job(db, device, job_id)
    if job.status in TERMINAL_STATUSES:
        raise invalid_state("This job has already finished")
    if payload["event_type"] == "cancel_acknowledged":
        if job.cancel_requested and job.status not in TERMINAL_STATUSES:
            _move(job, "cancelled")
            job.error_summary = "Cancelled at a safe checkpoint."
    _event(
        db,
        job,
        payload["event_type"],
        payload.get("message") or payload["event_type"],
        progress=payload.get("progress"),
        tool=payload.get("tool"),
        details=payload.get("details") or {},
    )
    db.commit()
    db.refresh(job)
    return job


def submit_verification(db: Session, device: AgentDevice, job_id: uuid.UUID, payload: dict) -> InstallationJob:
    job = _device_job(db, device, job_id)
    if job.status == "installing":
        _move(job, "verifying")
    if job.status != "verifying":
        raise invalid_state("This job is not ready for verification")
    revision = db.get(EnvironmentRevision, job.revision_id)
    environment = environment_by_id(db, revision.environment_id)
    requirements = _requirements(revision)
    observations = {item["tool"]: item for item in payload.get("tools") or []}
    failures = {item["tool"]: item for item in payload.get("install_failures") or []}
    results = []
    install_failed = False
    unmet = False
    for requirement in requirements:
        observed = observations.get(requirement["tool"], {})
        failure = failures.get(requirement["tool"])
        try:
            if requirement["tool"] == "docker_engine":
                passed = bool(observed.get("functional")) and bool(observed.get("engine_running"))
            else:
                passed = (
                    bool(observed.get("installed"))
                    and bool(observed.get("functional"))
                    and version_satisfies(observed.get("version"), requirement["version_constraint"])
                )
        except VersionError:
            passed = False
        if failure and failure["category"] in {"installer_failed", "integrity_mismatch", "timeout"}:
            passed = False
            if requirement["mandatory"]:
                install_failed = True
        elif not passed and requirement["mandatory"]:
            unmet = True
        message = (failure or {}).get("message") or observed.get("uncertainty") or ""
        results.append(
            {
                "tool": requirement["tool"],
                "required_constraint": requirement["version_constraint"],
                "detected_version": observed.get("version"),
                "outcome": "pass" if passed else "fail",
                "mandatory": requirement["mandatory"],
                "details": redact({"message": message, "functional": observed.get("functional")}),
            }
        )
        db.add(
            VerificationResult(
                job_id=job.id,
                tool=requirement["tool"],
                required_constraint=requirement["version_constraint"],
                detected_version=observed.get("version"),
                outcome="pass" if passed else "fail",
                mandatory=requirement["mandatory"],
                details=redact({"message": message}),
            )
        )
    if job.cancel_requested:
        final = "cancelled"
        job.error_summary = "Cancelled before completion."
    elif install_failed:
        final = "failed"
        job.error_summary = _summary(results, True)
    elif unmet:
        final = "needs_attention"
        job.error_summary = _summary(results, True)
    else:
        final = "completed"
        job.error_summary = _summary(results, False)
    _move(job, final)
    _event(db, job, "verification_reported", job.error_summary or "Verification finished")
    current = environment.current_published_revision_id == job.revision_id
    readiness = readiness_from_results(requirements, results, current)
    if final == "completed":
        compliance = readiness
    elif final == "cancelled":
        compliance = "not_ready"
    else:
        compliance = "needs_attention" if final == "needs_attention" else "failed"
    _set_compliance(db, job, environment.id, compliance, {"results": results, "job_status": final})
    notify(
        db,
        job.student_id,
        "job_completed" if final == "completed" else "job_failed",
        {"job_id": str(job.id), "status": final, "summary": job.error_summary},
    )
    course = db.get(Course, environment.course_id)
    if course:
        notify(
            db,
            course.instructor_id,
            "job_completed" if final == "completed" else "job_failed",
            {"job_id": str(job.id), "status": final, "summary": job.error_summary, "student_id": str(job.student_id)},
        )
    db.commit()
    db.refresh(job)
    return job


def _summary(results: list[dict], problems_only: bool) -> str | None:
    messages = []
    for result in results:
        if problems_only and result["outcome"] == "pass":
            continue
        if result["outcome"] != "pass":
            detail = result["details"].get("message") or "check failed"
            messages.append(f"{result['tool']}: {detail}" if detail else result["tool"])
    text = "; ".join(messages)[:500]
    return text or None


def _device_job(db: Session, device: AgentDevice, job_id: uuid.UUID) -> InstallationJob:
    job = job_by_id(db, job_id)
    if not job or job.device_id != device.id:
        raise not_found("Job not found")
    return job


def _expire_if_stale(db: Session, settings: Settings, job: InstallationJob) -> None:
    if job.status not in {"installing", "verifying"}:
        return
    device = db.get(AgentDevice, job.device_id)
    if not device or not device.last_seen_at:
        return
    if utcnow() - device.last_seen_at > timedelta(seconds=settings.job_stale_seconds):
        _move(job, "needs_attention")
        job.error_summary = "The agent disconnected before the job finished."
        _event(db, job, "agent_disconnected", job.error_summary)
        db.commit()


def student_environments(db: Session, user: User) -> list[dict]:
    rows = db.execute(
        select(Environment, Course)
        .join(Course, Course.id == Environment.course_id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == user.id, Enrollment.status == "active")
        .order_by(Course.name, Environment.name)
    )
    payload = []
    for environment, course in rows:
        state = compliance_for(db, user.id, environment.id)
        payload.append(
            {
                "environment_id": environment.id,
                "name": environment.name,
                "description": environment.description,
                "course_id": course.id,
                "course_name": course.name,
                "class_code": course.class_code,
                "published_revision_id": environment.current_published_revision_id,
                "status": state.status if state else "not_checked",
                "summary": state.summary if state else {},
            }
        )
    return payload


def verification_for(db: Session, user: User, job_id: uuid.UUID) -> list[VerificationResult]:
    job = _load_authorized(db, user, job_id)
    return verification_results(db, job.id)


def preview_plan(db: Session, settings: Settings, user: User, environment_id: uuid.UUID, detection: dict) -> dict:
    environment = environment_by_id(db, environment_id)
    if not environment:
        raise not_found("Environment not found")
    course = db.get(Course, environment.course_id)
    allowed = user.role == "admin" or (course and course.instructor_id == user.id)
    if not allowed and not active_enrollment(db, user.id, environment.course_id):
        raise forbidden("You cannot preview this environment")
    revision = _published_revision(db, environment)
    return build_plan(_requirements(revision), detection, get_catalog(settings))
