"""Installation planning from a published revision and a detection report."""

from __future__ import annotations

import uuid

from app.domain.catalog import ToolCatalog
from app.domain.versions import VersionError, constraint_is_exact, version_satisfies

ACTION_KEYS = {
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


class PlanError(ValueError):
    pass


def _observation(detection: dict, tool_id: str) -> dict:
    tools = detection.get("tools") if isinstance(detection, dict) else None
    if not isinstance(tools, list):
        return {}
    for item in tools:
        if isinstance(item, dict) and item.get("tool") == tool_id:
            return item
    return {}


def _action(**kwargs) -> dict:
    unknown = set(kwargs) - ACTION_KEYS
    if unknown:
        raise PlanError(f"Plan action contains unsupported fields: {sorted(unknown)}")
    return kwargs


def build_plan(requirements: list[dict], detection: dict, catalog: ToolCatalog) -> dict:
    actions = []
    uncertainties = []
    required_ids = {item["tool"] for item in requirements}
    for requirement in requirements:
        tool_id = requirement["tool"]
        constraint = requirement["version_constraint"]
        mandatory = bool(requirement["mandatory"])
        observed = _observation(detection, tool_id)
        installed = bool(observed.get("installed"))
        functional = bool(observed.get("functional"))
        detected_version = observed.get("version")
        entry = catalog.tool(tool_id)
        if entry is None:
            raise PlanError(f"Unknown tool '{tool_id}'")

        satisfied = False
        try:
            satisfied = installed and functional and version_satisfies(detected_version, constraint)
        except VersionError as exc:
            raise PlanError(str(exc)) from exc

        if tool_id == "docker_engine":
            running = bool(observed.get("engine_running"))
            satisfied = running and functional
            if satisfied:
                actions.append(
                    _action(
                        id=str(uuid.uuid4()),
                        operation="reuse",
                        tool=tool_id,
                        version=detected_version,
                        package_id=None,
                        reason="Docker engine responded to docker info.",
                        impact="No installation is required.",
                        requires_elevation=False,
                        requires_reboot=False,
                        approval_required=False,
                        risks=[],
                        acknowledgements=[],
                    )
                )
                continue
            actions.append(
                _action(
                    id=str(uuid.uuid4()),
                    operation="verify_only",
                    tool=tool_id,
                    version=None,
                    package_id=None,
                    reason="The Docker engine is not running or could not be confirmed.",
                    impact="Docker Desktop installation does not start the engine. Readiness stays incomplete until docker info succeeds.",
                    requires_elevation=False,
                    requires_reboot=False,
                    approval_required=False,
                    risks=["A reboot or a manual start of Docker Desktop may be required."],
                    acknowledgements=[],
                )
            )
            uncertainties.append("Docker engine readiness is separate from the Docker CLI and Desktop installer.")
            continue

        if satisfied:
            actions.append(
                _action(
                    id=str(uuid.uuid4()),
                    operation="reuse",
                    tool=tool_id,
                    version=detected_version,
                    package_id=None,
                    reason=f"Detected {entry.display_name} {detected_version} satisfies {constraint}.",
                    impact="The existing installation is kept. Nothing is replaced.",
                    requires_elevation=False,
                    requires_reboot=False,
                    approval_required=False,
                    risks=[],
                    acknowledgements=[],
                )
            )
            continue

        if installed and observed.get("uncertainty") and not satisfied:
            actions.append(
                _action(
                    id=str(uuid.uuid4()),
                    operation="unsupported",
                    tool=tool_id,
                    version=detected_version,
                    package_id=None,
                    reason=observed.get("uncertainty") or "The detected installation is uncertain.",
                    impact="No installation will run over an installation whose version could not be confirmed.",
                    requires_elevation=False,
                    requires_reboot=False,
                    approval_required=False,
                    risks=["Readiness stays incomplete until the version can be confirmed." if mandatory else ""],
                    acknowledgements=[],
                )
            )
            continue

        if entry.strategy == "verify_only":
            node_present = _observation(detection, "node").get("installed")
            if tool_id == "npm" and ("node" in required_ids or node_present):
                actions.append(
                    _action(
                        id=str(uuid.uuid4()),
                        operation="verify_only",
                        tool=tool_id,
                        version=None,
                        package_id=None,
                        reason="npm is verified with Node.js and is not installed separately.",
                        impact="After Node.js is available, npm is checked again. A mismatch is reported instead of installing a different npm.",
                        requires_elevation=False,
                        requires_reboot=False,
                        approval_required=False,
                        risks=[],
                        acknowledgements=[],
                    )
                )
                continue
            actions.append(
                _action(
                    id=str(uuid.uuid4()),
                    operation="unsupported",
                    tool=tool_id,
                    version=detected_version,
                    package_id=None,
                    reason=entry.notes or f"{entry.display_name} cannot be installed by this platform.",
                    impact="No change will be made.",
                    requires_elevation=False,
                    requires_reboot=False,
                    approval_required=False,
                    risks=["A mandatory unsupported requirement blocks readiness." if mandatory else "Optional requirement will be reported and skipped."],
                    acknowledgements=[],
                )
            )
            continue

        if constraint == "present":
            target = catalog.newest_match(tool_id, ">=0.0") if entry.versions else None
        else:
            exact = constraint_is_exact(constraint)
            target = catalog.version(tool_id, exact) if exact else catalog.newest_match(tool_id, constraint)
        if target is None:
            actions.append(
                _action(
                    id=str(uuid.uuid4()),
                    operation="unsupported",
                    tool=tool_id,
                    version=detected_version,
                    package_id=None,
                    reason=f"No catalog version of {entry.display_name} satisfies {constraint}.",
                    impact="The platform will not substitute a different version.",
                    requires_elevation=False,
                    requires_reboot=False,
                    approval_required=False,
                    risks=["Readiness stays incomplete for a mandatory requirement." if mandatory else ""],
                    acknowledgements=[],
                )
            )
            continue

        existing = f" Existing {detected_version} is retained." if installed and detected_version else ""
        actions.append(
            _action(
                id=str(uuid.uuid4()),
                operation="install",
                tool=tool_id,
                version=target.version,
                package_id=target.winget_id,
                reason=f"Install catalog version {target.version} because the detected state does not satisfy {constraint}.",
                impact=target.impact + existing,
                requires_elevation=target.requires_elevation,
                requires_reboot=target.requires_reboot,
                approval_required=True,
                risks=[
                    "Windows may show a User Account Control prompt. The platform never receives the administrator password.",
                    "The existing installation is not uninstalled.",
                ],
                acknowledgements=list(target.acknowledgements),
            )
        )

    approval_required = any(item["approval_required"] for item in actions)
    acknowledgements = sorted({ack for item in actions for ack in item["acknowledgements"]})
    return {
        "actions": actions,
        "approval_required": approval_required,
        "required_acknowledgements": acknowledgements,
        "uncertainties": uncertainties,
        "detection": detection,
    }


def detection_drift(previous: dict | None, current: dict) -> bool:
    if not previous:
        return False

    def snapshot(payload: dict) -> dict:
        items = {}
        for item in payload.get("tools") or []:
            if isinstance(item, dict) and item.get("tool"):
                items[item["tool"]] = (
                    bool(item.get("installed")),
                    item.get("version"),
                    bool(item.get("functional")),
                    bool(item.get("engine_running")),
                )
        return items

    return snapshot(previous) != snapshot(current)
