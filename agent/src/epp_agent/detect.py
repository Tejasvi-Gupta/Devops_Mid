"""Local tool detection. This module does not install or change software."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from epp_agent.versions import extract_version


def run_command(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _observation(tool: str, installed: bool, version: str | None, functional: bool, **extra) -> dict:
    return {
        "tool": tool,
        "installed": installed,
        "version": version,
        "functional": functional,
        "executable": extra.get("executable"),
        "engine_running": extra.get("engine_running"),
        "uncertainty": extra.get("uncertainty"),
    }


def detect_with(run) -> dict:
    tools = []
    code, output = _try(run, ["python", "--version"])
    version = extract_version("python", output) if code == 0 else None
    tools.append(_observation("python", code == 0, version, code == 0 and version is not None))

    code, output = _try(run, ["node", "--version"])
    version = extract_version("node", output) if code == 0 else None
    tools.append(_observation("node", code == 0, version, code == 0 and version is not None))

    code, output = _try(run, ["npm", "--version"])
    version = extract_version("npm", output) if code == 0 else None
    tools.append(_observation("npm", code == 0, version, code == 0 and version is not None))

    code, output = _try(run, ["git", "--version"])
    version = extract_version("git", output) if code == 0 else None
    tools.append(_observation("git", code == 0, version, code == 0 and version is not None, executable="git"))

    desktop_installed = _desktop_installed()
    tools.append(
        _observation(
            "docker",
            desktop_installed,
            None,
            False,
            uncertainty=(
                "Docker Desktop is present, but its product version was not read. "
                "docker --version is not treated as the Desktop version."
                if desktop_installed
                else None
            ),
        )
    )
    info_code, _info = _try(run, ["docker", "info"])
    cli_code, cli_output = _try(run, ["docker", "--version"])
    cli_version = extract_version("docker", cli_output) if cli_code == 0 else None
    tools.append(
        _observation(
            "docker_engine",
            cli_code == 0,
            cli_version,
            info_code == 0,
            engine_running=info_code == 0,
            uncertainty=None if info_code == 0 else "docker info did not succeed, so the engine is not ready.",
        )
    )
    return {"tools": tools}


def _try(run, args: list[str]) -> tuple[int, str]:
    try:
        return run(args)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def _desktop_installed() -> bool:
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"
    return candidate.exists()
