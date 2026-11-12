"""Version extraction for tool output. Comparison rules live in the API."""

from __future__ import annotations

import re

_GENERIC = re.compile(r"(\d+(?:\.\d+){1,3})")
_GIT = re.compile(r"(\d+\.\d+\.\d+)(?:\.windows\.(\d+))?", re.IGNORECASE)


def extract_version(tool: str, raw: str) -> str | None:
    if tool == "git":
        match = _GIT.search(raw)
        if not match:
            return None
        return f"{match.group(1)}.{match.group(2)}" if match.group(2) else match.group(1)
    match = _GENERIC.search(raw)
    return match.group(1) if match else None
