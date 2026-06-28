"""Constants for the ComfoSpot integration."""
from __future__ import annotations

DOMAIN = "comfospot"

# Network
DISCOVERY_PORT = 9987
CONTROL_PORT = 9986
DEFAULT_PORT = CONTROL_PORT

# Fan stages
MIN_STAGE = 1
MAX_STAGE = 4

# Zone property IDs (FlakeVentilationZone, abbc9241-...-776d)
PID_SPEED = 0x2011        # float, fan stage 0..4
PID_MODE = 0x2020         # uint8, direction in the high nibble
PID_TARGET_TEMP = 0x2030  # float, target temperature
PID_NAME = 0x2004         # string, user-given zone name (e.g. "Zone 1")
PID_HUMIDITY = 0x1040     # float, indoor relative humidity (%)
PID_TEMPERATURE = 0x1042  # float, indoor temperature (degC)

# Object framework property IDs
PID_OBJ_UUID = 0x1001     # query key (uuid)
PID_OBJ_ADDR = 0x1002     # assigned object/client address

# System object property IDs (FlakeVentilationSystem, abbc9241-...-776c)
PID_SYS_CO2 = 0x1041        # float, air quality / CO2 (ppm)
PID_SYS_RUN_HOURS = 0x1005  # uint32, system operating hours
PID_SYS_FIRMWARE = 0x2101   # string, firmware version
PID_UNKNOWN_1043 = 0x1043   # float, unknown – likely internal temperature or motor temp

# Ventilation mode values for PID_MODE (low nibble; high nibble = auto-direction)
# 0x00 = Abluft  – both fans extract  (2 arrows left)
# 0x01 = Zuluft  – both fans supply   (2 arrows right)
# 0x02 = Wechsel – alternating supply/exhaust (crossing arrows)
MODES: dict[str, int] = {
    "exhaust":     0x00,
    "supply":      0x01,
    "alternating": 0x02,
}
MODES_INV: dict[int, str] = {v: k for k, v in MODES.items()}

# Zone FlakeObject UUID base (last byte varies per zone/system object)
ZONE_UUID_BASE = bytes.fromhex("abbc92414886407f8e36e26d0b6477")  # 15 bytes
ZONE_UUID_LAST_RANGE = range(0x6C, 0x74)
