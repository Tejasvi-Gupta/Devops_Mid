"""Agent polling routes. These accept a device credential, not a user session."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, current_device, settings_dep
from app.core.config import Settings
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import AgentDevice
from app.schemas.dto import AgentEventIn, DetectionIn, DeviceOut, PairIn, PairOut, VerificationIn
from app.services import device_service, job_service

router = APIRouter(tags=["agent"])


@router.post("/devices/pair", response_model=PairOut, status_code=201)
def pair(payload: PairIn, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    rate_limiter.check(f"pair:{client_ip(request)}", settings.pairing_rate_limit, settings.pairing_rate_window_seconds)
    device, credential = device_service.pair_device(db, payload.code, payload.display_name, payload.platform)
    return PairOut(device=DeviceOut.model_validate(device), device_credential=credential)


@router.get("/agent/work")
def work(
    device: AgentDevice = Depends(current_device),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    job = job_service.agent_work(db, settings, device)
    if not job:
        return {"job": None}
    return {"job": job_service.public_job(db, device_user(db, device), job)}


def device_user(db: Session, device: AgentDevice):
    from app.models import User

    return db.get(User, device.student_id)


@router.post("/agent/jobs/{job_id}/claim")
def claim(job_id: uuid.UUID, device: AgentDevice = Depends(current_device), db: Session = Depends(get_db)):
    job = job_service.claim(db, device, job_id)
    return job_service.public_job(db, device_user(db, device), job)


@router.post("/agent/jobs/{job_id}/detection")
def detection(
    job_id: uuid.UUID,
    payload: DetectionIn,
    device: AgentDevice = Depends(current_device),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    job = job_service.submit_detection(db, settings, device, job_id, payload.model_dump())
    return job_service.public_job(db, device_user(db, device), job)


@router.post("/agent/jobs/{job_id}/start")
def start(job_id: uuid.UUID, device: AgentDevice = Depends(current_device), db: Session = Depends(get_db)):
    job = job_service.start_install(db, device, job_id)
    return job_service.public_job(db, device_user(db, device), job)


@router.post("/agent/jobs/{job_id}/events")
def events(
    job_id: uuid.UUID,
    payload: AgentEventIn,
    device: AgentDevice = Depends(current_device),
    db: Session = Depends(get_db),
):
    job = job_service.agent_event(db, device, job_id, payload.model_dump())
    return job_service.public_job(db, device_user(db, device), job)


@router.post("/agent/jobs/{job_id}/verification")
def verification(
    job_id: uuid.UUID,
    payload: VerificationIn,
    device: AgentDevice = Depends(current_device),
    db: Session = Depends(get_db),
):
    job = job_service.submit_verification(db, device, job_id, payload.model_dump())
    return job_service.public_job(db, device_user(db, device), job)
