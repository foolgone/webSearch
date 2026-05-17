"""Run-level observability helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any
from uuid import uuid4

from services.logging import log_event


@dataclass(slots=True, frozen=True)
class RunEvent:
	name: str
	stage: str
	message: str
	timestamp: float
	details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunTelemetry:
	"""Collect structured events and stage durations for a single run."""

	run_id: str = field(default_factory=lambda: uuid4().hex[:12])
	started_at: float = field(default_factory=perf_counter)
	ended_at: float | None = None
	events: list[RunEvent] = field(default_factory=list)
	stage_durations: dict[str, float] = field(default_factory=dict)
	_stage_started_at: dict[str, float] = field(default_factory=dict, init=False, repr=False)

	def emit(self, name: str, *, stage: str = "core", message: str = "", **details: Any) -> None:
		now = perf_counter()
		self.events.append(
			RunEvent(
				name=name,
				stage=stage,
				message=message,
				timestamp=now,
				details=dict(details),
			),
		)
		log_event(message or name, stage=stage, run_id=self.run_id, event=name, **details)

	def start_stage(self, stage: str, **details: Any) -> None:
		self._stage_started_at[stage] = perf_counter()
		self.emit("stage_started", stage=stage, message=f"{stage} started", **details)

	def end_stage(self, stage: str, **details: Any) -> None:
		started_at = self._stage_started_at.pop(stage, None)
		if started_at is not None:
			self.stage_durations[stage] = perf_counter() - started_at
		self.emit("stage_finished", stage=stage, message=f"{stage} finished", duration_seconds=self.stage_durations.get(stage, 0.0), **details)

	def finish(self) -> None:
		self.ended_at = perf_counter()
		self.emit("run_finished", stage="core", message="run finished", elapsed_seconds=self.elapsed_seconds())

	def elapsed_seconds(self) -> float:
		stop_time = self.ended_at if self.ended_at is not None else perf_counter()
		return stop_time - self.started_at

	def to_dict(self) -> dict[str, Any]:
		return {
			"run_id": self.run_id,
			"started_at": self.started_at,
			"ended_at": self.ended_at,
			"elapsed_seconds": self.elapsed_seconds(),
			"stage_durations": dict(self.stage_durations),
			"events": [
				{
					"name": event.name,
					"stage": event.stage,
					"message": event.message,
					"timestamp": event.timestamp,
					"details": dict(event.details),
				}
				for event in self.events
			],
		}