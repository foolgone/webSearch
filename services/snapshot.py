"""State snapshot helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def snapshot_state(state: dict[str, Any]) -> dict[str, Any]:
    snapshot = deepcopy(state)
    snapshot["_snapshot_kind"] = "state"
    return snapshot


def restore_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    restored = deepcopy(snapshot)
    restored.pop("_snapshot_kind", None)
    return restored
