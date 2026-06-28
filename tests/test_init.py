"""Tests for __init__.py stale-entity cleanup."""
import re
import sys

sys.path.insert(0, "custom_components")

from comfospot import _STALE_UID_PATTERNS


class TestStaleUidPatterns:
    def _matches(self, uid: str) -> bool:
        return any(p.search(uid) for p in _STALE_UID_PATTERNS)

    # --- should be removed ---
    def test_system_devices(self):
        assert self._matches("abc123_system_devices")

    def test_zone_run_hours_single_digit(self):
        assert self._matches("abc123_zone8_run_hours")

    def test_zone_run_hours_multi_digit(self):
        assert self._matches("abc123_zone12_run_hours")

    # --- must NOT be removed ---
    def test_system_run_hours_kept(self):
        """The new system sensor must not be removed."""
        assert not self._matches("abc123_system_run_hours")

    def test_co2_kept(self):
        assert not self._matches("abc123_system_co2")

    def test_zone_temperature_kept(self):
        assert not self._matches("abc123_zone8_temperature")

    def test_zone_humidity_kept(self):
        assert not self._matches("abc123_zone8_humidity")

    def test_unknown_1043_kept(self):
        assert not self._matches("abc123_system_unknown_1043")
