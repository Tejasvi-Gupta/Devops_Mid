"""Redaction helpers for logs, diagnostics, and instructor views."""

from __future__ import annotations

import re

_SECRET_TEXT = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|credential|authorization|bearer|cookie)\s*[:=]\s*\S+"
)
_BEARER = re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/=]+")
_DEVICE = re.compile(r"\bdvc_[a-z0-9\-_]+\b", re.IGNORECASE)
_SENSITIVE_KEYS = (
    "password",
    "secret",
    "token",
    "credential",
    "authorization",
    "cookie",
    "hash",
    "code",
)
_MACHINE_KEYS = ("executable", "path", "stdout", "stderr", "command", "args", "traceback")
MAX_TEXT = 2000


def redact_text(value: str) -> str:
    text = _BEARER.sub("bearer [redacted]", value)
    text = _DEVICE.sub("[redacted]", text)
    text = _SECRET_TEXT.sub(lambda match: match.group(1) + "=[redacted]", text)
    if len(text) > MAX_TEXT:
        return text[:MAX_TEXT] + "…[truncated]"
    return text


def redact(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(part in str(key).lower() for part in _SENSITIVE_KEYS):
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def strip_machine_details(value):
    redacted = redact(value)
    if isinstance(redacted, dict):
        return {
            key: strip_machine_details(item)
            for key, item in redacted.items()
            if str(key).lower() not in _MACHINE_KEYS
        }
    if isinstance(redacted, list):
        return [strip_machine_details(item) for item in redacted]
    return redacted
