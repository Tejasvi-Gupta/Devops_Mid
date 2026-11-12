"""Trusted catalog and allowlisted winget commands."""

from __future__ import annotations

import json
from pathlib import Path

ALLOWED_ACTION_KEYS = {
    "id",
    "operation",
    "tool",
    "version",
    "package_id",
    "reason",
    "impact",
    "requires_elevation",
    "requires_reboot",
    "approval_required",
    "risks",
    "acknowledgements",
}


class RejectedAction(ValueError):
    pass


def find_catalog() -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / "catalog" / "tools.json",
        Path(__file__).resolve().parents[2] / "catalog" / "tools.json",
        Path("catalog/tools.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_catalog(path: Path | None = None) -> dict:
    return json.loads((path or find_catalog()).read_text(encoding="utf-8"))


def catalog_version(catalog: dict, tool: str, version: str) -> dict | None:
    for item in catalog["tools"]:
        if item["id"] == tool:
            for entry in item.get("versions", []):
                if entry["version"] == version:
                    return entry
    return None


def build_winget_command(action: dict, catalog: dict) -> list[str]:
    extra = set(action) - ALLOWED_ACTION_KEYS
    if extra or action.get("command") or action.get("shell") or action.get("args"):
        raise RejectedAction("The agent rejected an action that was not on the allowlist")
    if action.get("operation") != "install":
        raise RejectedAction("Only catalog install actions can be executed")
    entry = catalog_version(catalog, action.get("tool", ""), action.get("version", ""))
    if not entry or action.get("package_id") != entry["winget_id"]:
        raise RejectedAction("The requested package does not match the trusted catalog")
    return [
        "winget",
        "install",
        "--id",
        entry["winget_id"],
        "--version",
        entry["version"],
        "--exact",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--disable-interactivity",
    ]


def manifest_matches(show_output: str, entry: dict) -> bool:
    url = ""
    digest = ""
    for line in show_output.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("installer url:"):
            url = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("installer sha256:"):
            digest = stripped.split(":", 1)[1].strip().lower()
    return url == entry["url"] and digest == entry["sha256"].lower()
