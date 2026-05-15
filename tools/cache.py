"""Cache placeholder."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float


_CACHE: dict[str, CacheEntry] = {}


def get_cached(key: str) -> Any:
    entry = _CACHE.get(key)
    if not entry:
        return None
    if entry.expires_at < time():
        _CACHE.pop(key, None)
        return None
    return entry.value


def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> None:
    expires_at = time() + max(1, ttl_seconds)
    _CACHE[key] = CacheEntry(value=value, expires_at=expires_at)


def clear_cache() -> None:
    _CACHE.clear()
