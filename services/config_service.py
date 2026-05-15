"""Configuration service."""

from __future__ import annotations

from config import settings


def get_settings():
    """Return the active application settings."""

    return settings


def get_max_rounds() -> int:
    return int(settings.max_rounds)


def get_request_timeout() -> int:
    return int(settings.request_timeout)


