"""Tests for __init__.py stale-entity cleanup."""
import re
import sys

sys.path.insert(0, "custom_components")

from comfospot import _STALE_UID_PATTERNS, _UID_MIGRATIONS


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
        """Migrated (renamed) in 0.1.8, so it must never be stale-removed."""
        assert not self._matches("abc123_system_co2")

    def test_zone_temperature_kept(self):
        assert not self._matches("abc123_zone8_temperature")

    def test_zone_humidity_kept(self):
        assert not self._matches("abc123_zone8_humidity")

    def test_unknown_1043_kept(self):
        """Migrated (renamed) in 0.1.8, so it must never be stale-removed."""
        assert not self._matches("abc123_system_unknown_1043")


class TestUidMigrations:
    def _migrated(self, uid: str) -> str:
        for old, new in _UID_MIGRATIONS.items():
            if uid.endswith(old):
                return uid[: -len(old)] + new
        return uid

    def test_co2_becomes_pressure(self):
        assert self._migrated("abc123_system_co2") == "abc123_system_pressure"

    def test_unknown_1043_becomes_air_quality(self):
        assert self._migrated("abc123_system_unknown_1043") == "abc123_system_air_quality"

    def test_unrelated_uid_untouched(self):
        assert self._migrated("abc123_zone8_humidity") == "abc123_zone8_humidity"

    def test_new_uids_not_migrated_again(self):
        assert self._migrated("abc123_system_pressure") == "abc123_system_pressure"
        assert self._migrated("abc123_system_air_quality") == "abc123_system_air_quality"
