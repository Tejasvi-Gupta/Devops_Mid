"""Request and response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    account_status: str
    instructor_status: str


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    requested_role: Literal["student", "instructor"] = "student"

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.lower().strip()

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Password must include a letter and a number")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.lower().strip()


class GoogleIn(BaseModel):
    id_token: str = Field(min_length=20)
    requested_role: Literal["student", "instructor"] = "student"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str
    user: UserPublic


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    class_code: str = Field(default="", max_length=64)


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    class_code: str
    instructor_id: uuid.UUID
    status: str
    created_at: datetime


class EnrollmentIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.lower().strip()


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: str
    created_at: datetime


class RequirementIn(BaseModel):
    tool: str
    version_constraint: str
    mandatory: bool = True
    install_strategy: Literal["winget", "verify_only"] | None = None
    config: dict = Field(default_factory=dict)
    verification: dict = Field(default_factory=dict)


class EnvironmentIn(BaseModel):
    course_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    requirements: list[RequirementIn] = Field(default_factory=list)


class RevisionOut(BaseModel):
    id: uuid.UUID
    environment_id: uuid.UUID
    revision_number: int
    publication_status: str
    specification: dict
    published_at: datetime | None


class EnvironmentOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    description: str
    current_published_revision_id: uuid.UUID | None
    revisions: list[RevisionOut]


class PairingIn(BaseModel):
    replace_existing: bool = False


class PairIn(BaseModel):
    code: str = Field(min_length=8, max_length=12)
    display_name: str = Field(min_length=1, max_length=200)
    platform: Literal["windows"] = "windows"


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    display_name: str
    platform: str
    status: str
    registered_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None


class PairOut(BaseModel):
    device: DeviceOut
    device_credential: str


class ToolObservation(BaseModel):
    tool: str
    installed: bool = False
    version: str | None = None
    executable: str | None = None
    functional: bool = False
    engine_running: bool | None = None
    uncertainty: str | None = None


class DetectionIn(BaseModel):
    tools: list[ToolObservation]


class JobCreateIn(BaseModel):
    environment_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=80)
    operation: Literal["provision", "verify"] = "provision"


class ApproveIn(BaseModel):
    acknowledgements: list[str] = Field(default_factory=list)


class InstallFailureIn(BaseModel):
    tool: str
    category: Literal[
        "installer_failed",
        "integrity_mismatch",
        "unsupported",
        "cancelled",
        "timeout",
        "needs_attention",
    ]
    message: str = Field(default="", max_length=500)


class VerificationIn(BaseModel):
    tools: list[ToolObservation]
    install_failures: list[InstallFailureIn] = Field(default_factory=list)


class AgentEventIn(BaseModel):
    event_type: Literal[
        "step_started",
        "step_finished",
        "step_failed",
        "recovery_attempted",
        "cancel_acknowledged",
    ]
    progress: int | None = Field(default=None, ge=0, le=100)
    tool: str | None = None
    message: str = Field(default="", max_length=500)
    details: dict = Field(default_factory=dict)


class RoleIn(BaseModel):
    role: Literal["student", "instructor", "admin"]


class PageOut(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
