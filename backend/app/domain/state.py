"""Job state machine."""

from __future__ import annotations

ACTIVE_STATUSES = {"pending", "planning", "awaiting_approval", "installing", "verifying"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "needs_attention"}
RETRYABLE_STATUSES = {"failed", "cancelled", "needs_attention"}

_TRANSITIONS = {
    "pending": {"planning", "cancelled", "failed", "needs_attention"},
    "planning": {"awaiting_approval", "verifying", "cancelled", "failed", "needs_attention"},
    "awaiting_approval": {
        "installing",
        "verifying",
        "planning",
        "cancelled",
        "failed",
        "needs_attention",
    },
    "installing": {"verifying", "failed", "cancelled", "needs_attention"},
    "verifying": {"completed", "failed", "needs_attention", "cancelled"},
}


def assert_transition(current: str, nxt: str) -> None:
    if nxt not in _TRANSITIONS.get(current, set()):
        raise ValueError(f"Cannot move a job from {current} to {nxt}")


def readiness_from_results(requirements: list[dict], results: list[dict], revision_matches: bool) -> str:
    if not revision_matches:
        return "needs_update"
    by_tool = {item["tool"]: item for item in results}
    mandatory_failed = False
    for requirement in requirements:
        if not requirement["mandatory"]:
            continue
        result = by_tool.get(requirement["tool"])
        if not result or result.get("outcome") != "pass":
            mandatory_failed = True
            break
    return "not_ready" if mandatory_failed else "ready"
