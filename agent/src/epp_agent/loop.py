"""One polling pass. Callers supply the detector, executor, and API client."""

from __future__ import annotations


def _snapshot(detection: dict | None) -> dict:
    items = {}
    for item in (detection or {}).get("tools") or []:
        items[item.get("tool")] = (item.get("installed"), item.get("version"), item.get("functional"), item.get("engine_running"))
    return items


def process_once(client, detector, executor) -> dict | None:
    payload = client.poll()
    job = payload.get("job") if payload else None
    if not job:
        return None
    if job["status"] in {"pending", "planning"}:
        job = client.submit_detection(job["id"], detector.detect())
    if job["status"] == "awaiting_approval":
        if job.get("approval_state") != "approved":
            return job
        fresh = detector.detect()
        if _snapshot(job.get("detection")) != _snapshot(fresh):
            return client.submit_detection(job["id"], fresh)
        installs = [item for item in job.get("plan", {}).get("actions", []) if item.get("operation") == "install"]
        if installs:
            job = client.start(job["id"])
            if job["status"] != "installing":
                return job
            for action in installs:
                current = client.get_job(job["id"])
                if current.get("cancel_requested"):
                    return client.event(job["id"], {"event_type": "cancel_acknowledged", "message": "Stopped before the next install step"})
                executor.execute(action)
        job = client.submit_verification(job["id"], detector.detect())
    elif job["status"] == "verifying":
        job = client.submit_verification(job["id"], detector.detect())
    return job
