"""Unit tests for client.py helper functions and _snapshot() logic."""
import struct
import sys

import pytest

sys.path.insert(0, "custom_components")

from comfospot.client import (
    _f32,
    _str_val,
    _u32,
    percentage_to_stage,
    stage_to_percentage,
)
from comfospot.const import (
    PID_HUMIDITY,
    PID_MODE,
    PID_SPEED,
    PID_SYS_AIR_QUALITY,
    PID_SYS_IAQ_ACCURACY,
    PID_SYS_PRESSURE,
    PID_SYS_RUN_HOURS,
    PID_TEMPERATURE,
)


# ---------------------------------------------------------------------------
# Helper: build a fake state dict entry the same way FlakeClient._handle does.
# state[(obj_addr, pid)] = (ptype, raw_bytes)
# ---------------------------------------------------------------------------

def _f32_entry(value: float) -> tuple[int, bytes]:
    return (9, struct.pack("<f", value))


def _u32_entry(value: int) -> tuple[int, bytes]:
    return (4, struct.pack("<I", value))


def _u8_entry(value: int) -> tuple[int, bytes]:
    return (6, bytes([value]))


def _str_entry(value: str) -> tuple[int, bytes]:
    return (14, value.encode("utf-8"))


# ---------------------------------------------------------------------------
# _f32
# ---------------------------------------------------------------------------

class TestF32:
    def test_normal(self):
        state = {(6, PID_SYS_PRESSURE): _f32_entry(967.0)}
        assert abs(_f32(state, (6, PID_SYS_PRESSURE)) - 967.0) < 0.01

    def test_missing_key(self):
        assert _f32({}, (6, PID_SYS_PRESSURE)) is None

    def test_wrong_length(self):
        state = {(6, PID_SYS_PRESSURE): (9, b"\x01\x02")}
        assert _f32(state, (6, PID_SYS_PRESSURE)) is None

    def test_bytearray_value(self):
        """Gateway sends bytearray, not bytes — both must work."""
        state = {(6, PID_SYS_PRESSURE): (9, bytearray(struct.pack("<f", 500.0)))}
        assert abs(_f32(state, (6, PID_SYS_PRESSURE)) - 500.0) < 0.01


# ---------------------------------------------------------------------------
# _u32
# ---------------------------------------------------------------------------

class TestU32:
    def test_run_hours(self):
        """Core regression: 624 h must be decoded from the system object."""
        state = {(6, PID_SYS_RUN_HOURS): _u32_entry(624)}
        assert _u32(state, (6, PID_SYS_RUN_HOURS)) == 624

    def test_zero(self):
        state = {(6, PID_SYS_RUN_HOURS): _u32_entry(0)}
        assert _u32(state, (6, PID_SYS_RUN_HOURS)) == 0

    def test_missing_key(self):
        assert _u32({}, (6, PID_SYS_RUN_HOURS)) is None

    def test_bytearray_value(self):
        """Gateway sends bytearray — must also work for u32."""
        raw = bytearray(struct.pack("<I", 624))
        state = {(6, PID_SYS_RUN_HOURS): (4, raw)}
        assert _u32(state, (6, PID_SYS_RUN_HOURS)) == 624

    def test_short_payload(self):
        state = {(6, PID_SYS_RUN_HOURS): (4, b"\x01\x02")}
        assert _u32(state, (6, PID_SYS_RUN_HOURS)) is None


# ---------------------------------------------------------------------------
# _str_val
# ---------------------------------------------------------------------------

class TestStrVal:
    def test_normal(self):
        state = {(6, 0x2101): _str_entry("G2SF")}
        assert _str_val(state, (6, 0x2101)) == "G2SF"

    def test_null_terminated(self):
        state = {(6, 0x2101): (14, b"G2SF\x00\x00")}
        assert _str_val(state, (6, 0x2101)) == "G2SF"

    def test_empty_string(self):
        state = {(6, 0x2101): (14, b"\x00")}
        assert _str_val(state, (6, 0x2101)) is None

    def test_missing_key(self):
        assert _str_val({}, (6, 0x2101)) is None


# ---------------------------------------------------------------------------
# _snapshot() logic — tested directly without a FlakeClient connection
# ---------------------------------------------------------------------------

def _make_live_state() -> dict:
    """Mirrors the state dict seen on the real device (from live dump)."""
    return {
        # --- system object (addr=6) ---
        (6, PID_SYS_PRESSURE):      _f32_entry(967.0),
        (6, PID_SYS_RUN_HOURS): _u32_entry(624),
        (6, PID_SYS_AIR_QUALITY): _f32_entry(31.36),
        (6, PID_SYS_IAQ_ACCURACY): _u8_entry(3),
        # no firmware (0x2101) in this capture
        # --- zone object (addr=8) ---
        (8, PID_SPEED):        _f32_entry(4.0),
        (8, PID_MODE):         _u8_entry(2),
        (8, PID_HUMIDITY):     _f32_entry(62.9),
        (8, PID_TEMPERATURE):  _f32_entry(20.0),
    }


def _snapshot(state: dict, zones: dict, sys_addrs: list) -> dict:
    """Exact copy of ComfoSpot._snapshot() for isolated testing."""
    from comfospot.client import _f32, _u8, _u32, _str_val
    from comfospot.const import (
        PID_HUMIDITY, PID_MODE, PID_SPEED,
        PID_SYS_AIR_QUALITY, PID_SYS_FIRMWARE, PID_SYS_IAQ_ACCURACY,
        PID_SYS_PRESSURE, PID_SYS_RUN_HOURS,
        PID_TARGET_TEMP, PID_TEMPERATURE,
    )
    result_zones = {}
    for addr, name in zones.items():
        result_zones[addr] = {
            "name": name,
            "speed": _f32(state, (addr, PID_SPEED)),
            "mode": state.get((addr, PID_MODE), (None, b"\x00"))[1][0]
                    if state.get((addr, PID_MODE)) else None,
            "humidity": _f32(state, (addr, PID_HUMIDITY)),
            "temperature": _f32(state, (addr, PID_TEMPERATURE)),
        }
    system = {
        "pressure": None,
        "air_quality": None,
        "iaq_accuracy": None,
        "run_hours": None,
        "firmware": None,
    }
    for addr in sys_addrs:
        if system["pressure"] is None:
            system["pressure"] = _f32(state, (addr, PID_SYS_PRESSURE))
        if system["air_quality"] is None:
            system["air_quality"] = _f32(state, (addr, PID_SYS_AIR_QUALITY))
        if system["iaq_accuracy"] is None:
            system["iaq_accuracy"] = _u8(state, (addr, PID_SYS_IAQ_ACCURACY))
        if system["run_hours"] is None:
            system["run_hours"] = _u32(state, (addr, PID_SYS_RUN_HOURS))
        if system["firmware"] is None:
            system["firmware"] = _str_val(state, (addr, PID_SYS_FIRMWARE))
    return {"zones": result_zones, "system": system}


class TestSnapshot:
    def setup_method(self):
        self.state = _make_live_state()
        self.zones = {8: "Zone 1"}
        self.sys_addrs = [6]

    def test_run_hours_is_not_none(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert data["system"]["run_hours"] is not None, (
            "run_hours must not be None — old zone-sensor code read from wrong PID/object"
        )

    def test_run_hours_value(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert data["system"]["run_hours"] == 624

    def test_pressure_value(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert abs(data["system"]["pressure"] - 967.0) < 0.1

    def test_air_quality_value(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert abs(data["system"]["air_quality"] - 31.36) < 0.01

    def test_iaq_accuracy_value(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert data["system"]["iaq_accuracy"] == 3

    def test_firmware_none_when_absent(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert data["system"]["firmware"] is None

    def test_zone_speed_and_mode(self):
        data = _snapshot(self.state, self.zones, self.sys_addrs)
        assert abs(data["zones"][8]["speed"] - 4.0) < 0.01
        assert data["zones"][8]["mode"] == 2

    def test_run_hours_missing_when_sys_addrs_empty(self):
        """If sys_addrs is empty (misconfiguration), run_hours must be None."""
        data = _snapshot(self.state, self.zones, sys_addrs=[])
        assert data["system"]["run_hours"] is None

    def test_run_hours_not_read_from_zone(self):
        """Zone object has 0x1005=1 — that must NOT leak into system run_hours."""
        state_with_zone_1005 = {**self.state, (8, PID_SYS_RUN_HOURS): _u32_entry(1)}
        data = _snapshot(state_with_zone_1005, self.zones, self.sys_addrs)
        assert data["system"]["run_hours"] == 624  # from system obj, not zone


# ---------------------------------------------------------------------------
# stage / percentage helpers
# ---------------------------------------------------------------------------

class TestStageHelpers:
    def test_stage_0_is_0_percent(self):
        assert stage_to_percentage(0) == 0

    def test_stage_max_is_100_percent(self):
        from comfospot.const import MAX_STAGE
        assert stage_to_percentage(MAX_STAGE) == 100

    def test_percentage_0_is_stage_0(self):
        assert percentage_to_stage(0) == 0

    def test_percentage_100_is_max_stage(self):
        from comfospot.const import MAX_STAGE
        assert percentage_to_stage(100) == MAX_STAGE

    def test_roundtrip(self):
        from comfospot.const import MAX_STAGE
        for stage in range(0, MAX_STAGE + 1):
            pct = stage_to_percentage(stage)
            back = percentage_to_stage(pct)
            assert back == stage, f"stage {stage} -> {pct}% -> {back}"
