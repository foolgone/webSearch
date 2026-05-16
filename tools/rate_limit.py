"""Rate limit utilities."""

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


def remaining_requests(key: str, limit: int = 5, window_seconds: int = 60) -> int:
    now = time()
    window_start = now - max(1, window_seconds)
    requests = _REQUEST_LOGS[key]
    while requests and requests[0] < window_start:
        requests.popleft()
    remaining = max(0, max(1, limit) - len(requests))
    return remaining


def get_rate_limit_state(key: str, limit: int = 5, window_seconds: int = 60) -> dict[str, int]:
    now = time()
    window_start = now - max(1, window_seconds)
    requests = _REQUEST_LOGS[key]
    while requests and requests[0] < window_start:
        requests.popleft()
    active_requests = len(requests)
    return {
        "limit": max(1, limit),
        "window_seconds": max(1, window_seconds),
        "active_requests": active_requests,
        "remaining_requests": max(0, max(1, limit) - active_requests),
    }


def reset_rate_limits() -> None:
    _REQUEST_LOGS.clear()
