"""Process-local rate limiter.

A single API process is the expected local and initial ECS task shape. A
multi-instance deployment should replace this with a shared store before it
is relied on for abuse protection across tasks.
"""

from __future__ import annotations

import time
from collections import defaultdict

from app.core.errors import rate_limited


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        recent = [stamp for stamp in self._hits[key] if now - stamp < window_seconds]
        if len(recent) >= limit:
            self._hits[key] = recent
            raise rate_limited()
        recent.append(now)
        self._hits[key] = recent

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter()
