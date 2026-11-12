"""Courses, enrollment, and instructor readiness."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, not_found
from app.models import ComplianceState, Course, Enrollment, Environment, User
from app.repositories.store import active_enrollment, course_by_id, user_by_email
from app.services.common import audit, notify


def _require_owner(course: Course, user: User) -> None:
    if user.role == "admin":
        return
    if course.instructor_id != user.id:
        raise forbidden("You do not manage this course")


def create_course(db: Session, user: User, name: str, description: str, class_code: str) -> Course:
    course = Course(
        name=name.strip(),
        description=description.strip(),
        class_code=class_code.strip(),
        instructor_id=user.id,
    )
    db.add(course)
    db.flush()
    audit(
        db,
        actor_id=user.id,
        action="course.create",
        target_type="course",
        target_id=str(course.id),
        outcome="success",
    )
    db.commit()
    db.refresh(course)
    return course


def list_courses(db: Session, user: User) -> list[Course]:
    if user.role == "admin":
        query = select(Course).order_by(Course.created_at.desc())
    elif user.role == "instructor" and user.instructor_status == "approved":
        query = select(Course).where(Course.instructor_id == user.id).order_by(Course.created_at.desc())
    else:
        query = (
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == user.id, Enrollment.status == "active")
            .order_by(Course.created_at.desc())
        )
    return list(db.scalars(query))


def get_course(db: Session, user: User, course_id: uuid.UUID) -> Course:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    if user.role == "admin" or course.instructor_id == user.id:
        return course
    if not active_enrollment(db, user.id, course.id):
        raise forbidden("You are not enrolled in this course")
    return course


def enroll(db: Session, user: User, course_id: uuid.UUID, email: str) -> Enrollment:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    _require_owner(course, user)
    student = user_by_email(db, email)
    if not student or student.account_status != "active" or student.role != "student":
        raise not_found("No active student account uses that email")
    existing = db.scalar(
        select(Enrollment).where(Enrollment.student_id == student.id, Enrollment.course_id == course.id)
    )
    if existing and existing.status == "active":
        raise conflict("That student is already enrolled")
    if existing:
        existing.status = "active"
        row = existing
    else:
        row = Enrollment(student_id=student.id, course_id=course.id)
        db.add(row)
    db.flush()
    environments = list(db.scalars(select(Environment).where(Environment.course_id == course.id)))
    if any(item.current_published_revision_id for item in environments):
        notify(
            db,
            student.id,
            "environment_assigned",
            {"course_id": str(course.id), "course_name": course.name},
        )
    audit(
        db,
        actor_id=user.id,
        action="enrollment.add",
        target_type="enrollment",
        target_id=str(row.id),
        outcome="success",
        context={"student_id": str(student.id), "course_id": str(course.id)},
    )
    db.commit()
    db.refresh(row)
    return row


def list_enrollments(db: Session, user: User, course_id: uuid.UUID) -> list[dict]:
    course = get_course(db, user, course_id)
    if user.role == "student" and course.instructor_id != user.id:
        raise forbidden("Students cannot list the class roster")
    rows = db.execute(
        select(Enrollment, User)
        .join(User, User.id == Enrollment.student_id)
        .where(Enrollment.course_id == course.id, Enrollment.status == "active")
        .order_by(User.name)
    )
    return [
        {
            "id": enrollment.id,
            "student_id": student.id,
            "name": student.name,
            "email": student.email,
            "status": enrollment.status,
        }
        for enrollment, student in rows
    ]


def readiness(db: Session, user: User, course_id: uuid.UUID) -> list[dict]:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    _require_owner(course, user)
    environments = list(db.scalars(select(Environment).where(Environment.course_id == course.id)))
    roster = list_enrollments(db, user, course_id)
    report = []
    for student in roster:
        env_rows = []
        for environment in environments:
            state = db.scalar(
                select(ComplianceState).where(
                    ComplianceState.student_id == student["student_id"],
                    ComplianceState.environment_id == environment.id,
                )
            )
            env_rows.append(
                {
                    "environment_id": environment.id,
                    "name": environment.name,
                    "published_revision_id": environment.current_published_revision_id,
                    "status": state.status if state else "not_checked",
                    "revision_id": state.revision_id if state else None,
                    "summary": state.summary if state else {},
                }
            )
        report.append({"student": student, "environments": env_rows})
    return report


def remove_enrollment(db: Session, user: User, course_id: uuid.UUID, enrollment_id: uuid.UUID) -> None:
    course = course_by_id(db, course_id)
    if not course:
        raise not_found("Course not found")
    _require_owner(course, user)
    row = db.get(Enrollment, enrollment_id)
    if not row or row.course_id != course.id:
        raise not_found("Enrollment not found")
    row.status = "removed"
    audit(
        db,
        actor_id=user.id,
        action="enrollment.remove",
        target_type="enrollment",
        target_id=str(row.id),
        outcome="success",
    )
    db.commit()
