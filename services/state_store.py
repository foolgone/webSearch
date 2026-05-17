"""Persistence helpers for saving and restoring research workflow state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from models import ResearchState


class StateStore(Protocol):
	def save_checkpoint(self, run_id: str, stage: str, state: ResearchState, *, is_final: bool = False) -> None:
		...

	def load_latest(self, run_id: str) -> ResearchState | None:
		...


@dataclass(slots=True)
class NullStateStore:
	def save_checkpoint(self, run_id: str, stage: str, state: ResearchState, *, is_final: bool = False) -> None:
		return None

	def load_latest(self, run_id: str) -> ResearchState | None:
		return None


@dataclass(slots=True)
class InMemoryStateStore:
	checkpoints: dict[str, list[ResearchState]] = field(default_factory=dict)

	def save_checkpoint(self, run_id: str, stage: str, state: ResearchState, *, is_final: bool = False) -> None:
		snapshot = dict(state)
		snapshot["_workflow_stage"] = stage
		snapshot["_is_final_checkpoint"] = is_final
		self.checkpoints.setdefault(run_id, []).append(snapshot)

	def load_latest(self, run_id: str) -> ResearchState | None:
		items = self.checkpoints.get(run_id, [])
		if not items:
			return None
		return dict(items[-1])


@dataclass(slots=True)
class PostgresStateStore:
	dsn: str
	schema: str = "public"
	_connection_factory: Any | None = None

	def __post_init__(self) -> None:
		if self._connection_factory is None:
			from psycopg import connect

			self._connection_factory = connect
		self._ensure_schema()

	def _connect(self):
		return self._connection_factory(self.dsn)

	def _qualified(self, table_name: str) -> str:
		return f'{self.schema}.{table_name}' if self.schema else table_name

	def _ensure_schema(self) -> None:
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
				cursor.execute(
					f"""
					CREATE TABLE IF NOT EXISTS {self._qualified('research_run_checkpoints')} (
						run_id TEXT NOT NULL,
						checkpoint_index INTEGER NOT NULL,
						stage TEXT NOT NULL,
						is_final BOOLEAN NOT NULL DEFAULT FALSE,
						state JSONB NOT NULL,
						created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
						PRIMARY KEY (run_id, checkpoint_index)
					)
					"""
				)
				cursor.execute(
					f"""
					CREATE TABLE IF NOT EXISTS {self._qualified('research_run_latest')} (
						run_id TEXT PRIMARY KEY,
						checkpoint_index INTEGER NOT NULL,
						stage TEXT NOT NULL,
						is_final BOOLEAN NOT NULL DEFAULT FALSE,
						updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
					)
					"""
				)
			connection.commit()

	def save_checkpoint(self, run_id: str, stage: str, state: ResearchState, *, is_final: bool = False) -> None:
		payload = json.dumps(state, ensure_ascii=False)
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					f"SELECT checkpoint_index FROM {self._qualified('research_run_latest')} WHERE run_id = %s",
					(run_id,),
				)
				row = cursor.fetchone()
				next_index = int(row[0]) + 1 if row else 1
				cursor.execute(
					f"""
					INSERT INTO {self._qualified('research_run_checkpoints')}
					(run_id, checkpoint_index, stage, is_final, state)
					VALUES (%s, %s, %s, %s, %s::jsonb)
					""",
					(run_id, next_index, stage, is_final, payload),
				)
				cursor.execute(
					f"""
					INSERT INTO {self._qualified('research_run_latest')}
					(run_id, checkpoint_index, stage, is_final, updated_at)
					VALUES (%s, %s, %s, %s, NOW())
					ON CONFLICT (run_id)
					DO UPDATE SET
						checkpoint_index = EXCLUDED.checkpoint_index,
						stage = EXCLUDED.stage,
						is_final = EXCLUDED.is_final,
						updated_at = EXCLUDED.updated_at
					""",
					(run_id, next_index, stage, is_final),
				)
			connection.commit()

	def load_latest(self, run_id: str) -> ResearchState | None:
		with self._connect() as connection:
			with connection.cursor() as cursor:
				cursor.execute(
					f"""
					SELECT state
					FROM {self._qualified('research_run_checkpoints')}
					WHERE run_id = %s
					ORDER BY checkpoint_index DESC
					LIMIT 1
					""",
					(run_id,),
				)
				row = cursor.fetchone()
				if not row:
					return None
				state = row[0]
				if isinstance(state, str):
					return json.loads(state)
				return state


def build_state_store(*, dsn: str | None, schema: str = "public") -> StateStore:
	if not dsn:
		return NullStateStore()
	return PostgresStateStore(dsn=dsn, schema=schema)