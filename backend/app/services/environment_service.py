"""Environment drafts, validation, and immutable publication."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import conflict, forbidden, not_found, validation_error
from app.domain.catalog import get_catalog
from app.domain.versions import VersionError, constraint_is_exact, validate_constraint
from app.models import Course, Environment, EnvironmentRevision, SoftwareRequirement, User
from app.repositories.store import (
    active_enrollment,
    compliance_for,
    course_by_id,
    environment_by_id,
    latest_revision_number,
    requirements_for,
)
from app.services.common import audit, notify, utcnow


def _owner_course(db: Session, user: User, course_id: uuid.UUID) -> Course:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    if user.role != "admin" and course.instructor_id != user.id:
        raise forbidden("You do not manage this course")
    return course


def normalize_requirements(settings: Settings, items: list[dict]) -> list[dict]:
    if not items:
        raise validation_error("Add at least one software requirement")
    catalog = get_catalog(settings)
    seen: set[str] = set()
    normalized = []
    for item in items:
        tool_id = item["tool"]
        if tool_id in seen:
            raise validation_error(f"{tool_id} is listed more than once")
        seen.add(tool_id)
        tool = catalog.tool(tool_id)
        if not tool:
            raise validation_error(f"Unknown tool '{tool_id}'")
        try:
            constraint = validate_constraint(item["version_constraint"])
        except VersionError as exc:
            raise validation_error(str(exc)) from exc
        strategy = item.get("install_strategy") or tool.strategy
        if strategy != tool.strategy:
            raise validation_error(f"{tool.display_name} uses the {tool.strategy} strategy")
        if tool_id == "npm" and constraint_is_exact(constraint):
            raise validation_error("npm cannot be pinned to an exact version")
        if tool_id == "docker_engine" and constraint != "present":
            raise validation_error("The Docker engine check only supports 'present'")
        if tool.strategy == "winget":
            exact = constraint_is_exact(constraint)
            if exact and not catalog.version(tool_id, exact):
                raise validation_error(f"{tool.display_name} {exact} is not in the supported catalog")
        normalized.append(
            {
                "tool": tool_id,
                "display_name": tool.display_name,
                "version_constraint": constraint,
                "mandatory": bool(item.get("mandatory", True)),
                "install_strategy": strategy,
                "config": item.get("config") or {},
                "verification": item.get("verification") or {},
            }
        )
    return normalized


def _visible(db: Session, user: User, environment: Environment) -> None:
    course = course_by_id(db, environment.course_id)
    if not course:
        raise not_found("Environment not found")
    if user.role == "admin" or course.instructor_id == user.id:
        return
    if not active_enrollment(db, user.id, course.id):
        raise forbidden("You are not enrolled in this course")


def create_environment(db: Session, settings: Settings, user: User, payload: dict) -> Environment:
    _owner_course(db, user, payload["course_id"])
    requirements = normalize_requirements(settings, payload.get("requirements") or [])
    environment = Environment(
        course_id=payload["course_id"],
        name=payload["name"].strip(),
        description=payload.get("description", "").strip(),
    )
    db.add(environment)
    db.flush()
    revision = EnvironmentRevision(
        environment_id=environment.id,
        revision_number=1,
        specification={"requirements": requirements},
        publication_status="draft",
    )
    db.add(revision)
    db.flush()
    _replace_requirement_rows(db, revision.id, requirements)
    audit(
        db,
        actor_id=user.id,
        action="environment.create",
        target_type="environment",
        target_id=str(environment.id),
        outcome="success",
    )
    db.commit()
    db.refresh(environment)
    return environment


def _replace_requirement_rows(db: Session, revision_id: uuid.UUID, requirements: list[dict]) -> None:
    for row in requirements_for(db, revision_id):
        db.delete(row)
    db.flush()
    for item in requirements:
        db.add(SoftwareRequirement(revision_id=revision_id, **item))


def update_draft(db: Session, settings: Settings, user: User, revision_id: uuid.UUID, items: list[dict]):
    revision = db.get(EnvironmentRevision, revision_id)
    if not revision:
        raise not_found("Revision not found")
    environment = environment_by_id(db, revision.environment_id)
    if not environment:
        raise not_found("Environment not found")
    _owner_course(db, user, environment.course_id)
    if revision.publication_status != "draft":
        raise conflict("Published revisions are immutable. Create a new revision.")
    requirements = normalize_requirements(settings, items)
    revision.specification = {"requirements": requirements}
    _replace_requirement_rows(db, revision.id, requirements)
    db.commit()
    db.refresh(revision)
    return revision


def publish(db: Session, user: User, revision_id: uuid.UUID) -> EnvironmentRevision:
    revision = db.get(EnvironmentRevision, revision_id)
    if not revision:
        raise not_found("Revision not found")
    environment = environment_by_id(db, revision.environment_id)
    if not environment:
        raise not_found("Environment not found")
    course = _owner_course(db, user, environment.course_id)
    if revision.publication_status == "published":
        raise conflict("This revision is already published")
    if not revision.specification.get("requirements"):
        raise validation_error("Add at least one software requirement before publishing")
    revision.publication_status = "published"
    revision.published_by = user.id
    revision.published_at = utcnow()
    environment.current_published_revision_id = revision.id
    environment.updated_at = utcnow()
    from app.models import Enrollment

    enrollments = list(
        db.scalars(
            select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.status == "active")
        )
    )
    for enrollment in enrollments:
        state = compliance_for(db, enrollment.student_id, environment.id)
        if state and state.revision_id and state.revision_id != revision.id and state.status == "ready":
            state.status = "needs_update"
            state.updated_at = utcnow()
        notify(
            db,
            enrollment.student_id,
            "revision_published",
            {
                "course_id": str(course.id),
                "environment_id": str(environment.id),
                "revision_id": str(revision.id),
                "revision_number": revision.revision_number,
            },
        )
    audit(
        db,
        actor_id=user.id,
        action="revision.publish",
        target_type="environment_revision",
        target_id=str(revision.id),
        outcome="success",
    )
    db.commit()
    db.refresh(revision)
    return revision


def new_draft(db: Session, user: User, environment_id: uuid.UUID) -> EnvironmentRevision:
    environment = environment_by_id(db, environment_id)
    if not environment:
        raise not_found("Environment not found")
    _owner_course(db, user, environment.course_id)
    number = latest_revision_number(db, environment.id) + 1
    source: dict = {"requirements": []}
    if environment.current_published_revision_id:
        current = db.get(EnvironmentRevision, environment.current_published_revision_id)
        if current:
            source = current.specification
    revision = EnvironmentRevision(
        environment_id=environment.id,
        revision_number=number,
        specification=source,
        publication_status="draft",
    )
    db.add(revision)
    db.flush()
    _replace_requirement_rows(db, revision.id, list(source.get("requirements") or []))
    db.commit()
    db.refresh(revision)
    return revision


def get_environment(db: Session, user: User, environment_id: uuid.UUID) -> tuple[Environment, list[EnvironmentRevision]]:
    environment = environment_by_id(db, environment_id)
    if not environment:
        raise not_found("Environment not found")
    _visible(db, user, environment)
    revisions = list(
        db.scalars(
            select(EnvironmentRevision)
            .where(EnvironmentRevision.environment_id == environment.id)
            .order_by(EnvironmentRevision.revision_number)
        )
    )
    if user.role == "student":
        revisions = [item for item in revisions if item.publication_status == "published"]
    return environment, revisions


def list_for_course(db: Session, user: User, course_id: uuid.UUID) -> list[Environment]:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    if user.role != "admin" and course.instructor_id != user.id and not active_enrollment(db, user.id, course.id):
        raise forbidden("You do not have access to this course")
    return list(db.scalars(select(Environment).where(Environment.course_id == course.id).order_by(Environment.name)))
