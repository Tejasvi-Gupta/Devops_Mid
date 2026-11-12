"""Windows agent command line."""

from __future__ import annotations

import argparse
import json
import os
import time

import httpx

from epp_agent.credentials import default_store
from epp_agent.detect import detect_with, run_command
from epp_agent.execute import WindowsInstaller
from epp_agent.loop import process_once


class ApiClient:
    def __init__(self, base_url: str, credential: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {credential}"}

    def poll(self) -> dict:
        response = httpx.get(f"{self.base_url}/api/v1/agent/work", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_job(self, job_id: str) -> dict:
        response = httpx.get(f"{self.base_url}/api/v1/agent/work", headers=self.headers, timeout=30)
        response.raise_for_status()
        job = response.json().get("job")
        return job if job and job["id"] == job_id else {"id": job_id, "cancel_requested": False, "status": "missing"}

    def submit_detection(self, job_id: str, detection: dict) -> dict:
        response = httpx.post(f"{self.base_url}/api/v1/agent/jobs/{job_id}/detection", headers=self.headers, json=detection, timeout=30)
        response.raise_for_status()
        return response.json()

    def start(self, job_id: str) -> dict:
        response = httpx.post(f"{self.base_url}/api/v1/agent/jobs/{job_id}/start", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def submit_verification(self, job_id: str, detection: dict) -> dict:
        response = httpx.post(
            f"{self.base_url}/api/v1/agent/jobs/{job_id}/verification",
            headers=self.headers,
            json={"tools": detection["tools"], "install_failures": []},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def event(self, job_id: str, payload: dict) -> dict:
        response = httpx.post(f"{self.base_url}/api/v1/agent/jobs/{job_id}/events", headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Environment provisioning Windows agent")
    parser.add_argument("command", choices=["detect", "pair", "run"])
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--code", default="")
    parser.add_argument("--name", default=os.environ.get("COMPUTERNAME", "Windows device"))
    args = parser.parse_args()
    if args.command == "detect":
        print(json.dumps(detect_with(run_command), indent=2))
        print("Detection only. No software was installed or changed.")
        return
    store = default_store()
    if args.command == "pair":
        response = httpx.post(
            f"{args.server.rstrip('/')}/api/v1/devices/pair",
            json={"code": args.code, "display_name": args.name, "platform": "windows"},
            timeout=30,
        )
        response.raise_for_status()
        credential = response.json()["device_credential"]
        store.save("device_credential", credential)
        store.save("server", args.server)
        print("Device paired. The credential was stored with Windows DPAPI and is not printed again.")
        return
    credential = store.load("device_credential")
    server = store.load("server") or args.server
    if not credential:
        raise SystemExit("Pair this device before running the agent.")
    client = ApiClient(server, credential)
    print("Agent is polling. Close this window to stop. It is not a Windows service.")
    while True:
        try:
            process_once(client, Detector(), WindowsInstaller())
            time.sleep(3)
        except httpx.HTTPError as exc:
            print(f"Network error: {exc.__class__.__name__}. Retrying.")
            time.sleep(10)


class Detector:
    def detect(self) -> dict:
        return detect_with(run_command)


if __name__ == "__main__":
    main()
