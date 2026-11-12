"""Shared version parsing and constraint checks.

Version strings are compared as numeric tuples. Text such as "latest" is
rejected instead of being treated as a comparable version.
"""

from __future__ import annotations

import re

_VERSION = re.compile(r"^\d+(?:\.\d+){1,3}$")
_SPEC = re.compile(r"^(==|>=|<=|>|<|!=)\s*(\d+(?:\.\d+){1,3})$")
_GIT = re.compile(r"(\d+\.\d+\.\d+)(?:\.windows\.(\d+))?", re.IGNORECASE)
_GENERIC = re.compile(r"(\d+(?:\.\d+){1,3})")


class VersionError(ValueError):
    pass


def parse_version(value: str) -> tuple[int, ...]:
    text = value.strip()
    if not _VERSION.match(text):
        raise VersionError(f"Unsupported version '{value}'")
    return tuple(int(part) for part in text.split("."))


def extract_version(tool: str, raw: str) -> str | None:
    text = raw.strip()
    if tool == "git":
        match = _GIT.search(text)
        if not match:
            return None
        base = match.group(1)
        return f"{base}.{match.group(2)}" if match.group(2) else base
    match = _GENERIC.search(text)
    if not match:
        return None
    try:
        parse_version(match.group(1))
    except VersionError:
        return None
    return match.group(1)


def _pad(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)), right + (0,) * (width - len(right))


def version_satisfies(version: str | None, constraint: str) -> bool:
    rule = constraint.strip().lower()
    if rule == "present":
        return bool(version)
    if not version:
        return False
    try:
        current = parse_version(version)
    except VersionError:
        return False
    parts = [part.strip() for part in constraint.split(",") if part.strip()]
    if not parts:
        raise VersionError("Version constraint is empty")
    for part in parts:
        match = _SPEC.match(part)
        if not match:
            raise VersionError(f"Unsupported version constraint '{constraint}'")
        op, raw = match.group(1), match.group(2)
        target = parse_version(raw)
        left, right = _pad(current, target)
        ok = {
            "==": left == right,
            "!=": left != right,
            ">": left > right,
            ">=": left >= right,
            "<": left < right,
            "<=": left <= right,
        }[op]
        if not ok:
            return False
    return True


def validate_constraint(constraint: str) -> str:
    text = constraint.strip()
    if text.lower() == "present":
        return "present"
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise VersionError("Version constraint is empty")
    for part in parts:
        if not _SPEC.match(part):
            raise VersionError(
                "Use present, or comparisons such as ==3.12.10 or >=3.12,<3.13"
            )
    return ",".join(parts)


def constraint_is_exact(constraint: str) -> str | None:
    parts = [part.strip() for part in constraint.split(",") if part.strip()]
    if len(parts) == 1 and parts[0].startswith("=="):
        return parts[0][2:].strip()
    return None
