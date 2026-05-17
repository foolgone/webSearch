"""Retry helpers for transient failures."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import Any, TypeVar

from services.logging import log_event


T = TypeVar("T")


def _default_retry_if(exc: Exception) -> bool:
	return not isinstance(exc, (NotImplementedError, ValueError, TypeError, KeyboardInterrupt, SystemExit))


def retry_operation(
	operation: str,
	func: Callable[[], T],
	*,
	attempts: int = 3,
	base_delay_seconds: float = 0.1,
	backoff_multiplier: float = 2.0,
	retry_if: Callable[[Exception], bool] | None = None,
	stage: str = "core",
) -> T:
	"""Run ``func`` with a bounded retry policy for transient failures."""

	if attempts < 1:
		raise ValueError("attempts must be at least 1")

	should_retry = retry_if or _default_retry_if
	delay_seconds = max(0.0, base_delay_seconds)
	last_error: Exception | None = None

	for attempt in range(1, attempts + 1):
		try:
			if attempt > 1:
				log_event(
					f"retrying {operation}",
					stage=stage,
					operation=operation,
					attempt=attempt,
					delay_seconds=round(delay_seconds, 3),
				)
			return func()
		except Exception as exc:  # noqa: BLE001 - retry boundary needs to observe transient failures
			last_error = exc
			if attempt >= attempts or not should_retry(exc):
				raise
			log_event(
				f"{operation} failed; scheduling retry",
				stage=stage,
				operation=operation,
				attempt=attempt,
				attempts=attempts,
				error=exc.__class__.__name__,
			)
			sleep(delay_seconds)
			delay_seconds *= max(backoff_multiplier, 1.0)

	if last_error is not None:
		raise last_error
	raise RuntimeError(f"{operation} failed without raising an exception")