"""Execution is opt-in and refuses to run during tests."""

from __future__ import annotations

import os
import subprocess

from epp_agent.commands import build_winget_command, load_catalog


class WindowsInstaller:
    def execute(self, action: dict) -> dict:
        if os.environ.get("EPP_AGENT_MODE") == "test":
            raise RuntimeError("Refusing to install software while EPP_AGENT_MODE=test")
        command = build_winget_command(action, load_catalog())
        completed = subprocess.run(command, check=False, timeout=1800)
        return {"ok": completed.returncode == 0, "returncode": completed.returncode, "retryable": False}
