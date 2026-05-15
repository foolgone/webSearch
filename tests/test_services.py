from __future__ import annotations

import time

from services.snapshot import restore_state, snapshot_state
from tools.cache import clear_cache, get_cached, set_cached
from tools.rate_limit import allow_request, reset_rate_limits


def test_cache_expiration():
	clear_cache()
	set_cached("key", "value", ttl_seconds=1)
	assert get_cached("key") == "value"
	time.sleep(1.1)
	assert get_cached("key") is None


def test_rate_limit_window():
	reset_rate_limits()
	assert allow_request("example", limit=2, window_seconds=60) is True
	assert allow_request("example", limit=2, window_seconds=60) is True
	assert allow_request("example", limit=2, window_seconds=60) is False


def test_snapshot_and_restore():
	original = {"user_query": "example topic", "tasks": ["a"]}
	snapshot = snapshot_state(original)
	restored = restore_state(snapshot)
	assert restored == original
	assert restored is not original
