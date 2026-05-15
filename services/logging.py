"""Logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def log_event(message: str, *, stage: str = "core") -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{timestamp}] [websearch] [{stage}] {message}")
