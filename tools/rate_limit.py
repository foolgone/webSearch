"""Rate limit placeholder."""

from __future__ import annotations

from collections import defaultdict, deque
from time import time


_REQUEST_LOGS: dict[str, deque[float]] = defaultdict(deque)


def allow_request(key: str, limit: int = 5, window_seconds: int = 60) -> bool:
    now = time()
    window_start = now - max(1, window_seconds)
    requests = _REQUEST_LOGS[key]
    while requests and requests[0] < window_start:
        requests.popleft()
    if len(requests) >= max(1, limit):
        return False
    requests.append(now)
    return True


def reset_rate_limits() -> None:
    _REQUEST_LOGS.clear()
