"""Logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _format_field(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return repr(value)
    return str(value)


def log_event(message: str, *, stage: str = "core", run_id: str | None = None, **fields: Any) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    parts = [f"[{timestamp}]", "[websearch]", f"[{stage}]"]
    if run_id:
        parts.append(f"[run:{run_id}]")
    parts.append(message)
    if fields:
        field_text = ", ".join(f"{key}={_format_field(value)}" for key, value in fields.items())
        parts.append(f"| {field_text}")
    print(" ".join(parts))
