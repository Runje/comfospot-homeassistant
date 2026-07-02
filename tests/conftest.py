"""Shared fixtures and HA-stub setup for ComfoSpot tests.

All HA modules are stubbed here so that custom_components.comfospot.* can be
imported without a real Home Assistant installation.
"""
import sys
import types


def _make_stub(*attrs, **kw_attrs):
    """Create a minimal stub module with the given attributes."""
    m = types.ModuleType("stub")
    for attr in attrs:
        setattr(m, attr, attr)  # e.g. PERCENTAGE = "PERCENTAGE"
    for k, v in kw_attrs.items():
        setattr(m, k, v)
    return m


# -- homeassistant stubs -------------------------------------------------
ha = types.ModuleType("homeassistant")
ha.core = _make_stub("HomeAssistant")
ha.config_entries = _make_stub("ConfigEntry")
ha.exceptions = _make_stub("ConfigEntryNotReady")
ha.const = _make_stub(
    "CONF_HOST", "CONF_PORT",
    PERCENTAGE="%",
    EntityCategory=type("EntityCategory", (), {"DIAGNOSTIC": "diagnostic"})(),
    UnitOfTemperature=type("UnitOfTemperature", (), {"CELSIUS": "°C"})(),
    UnitOfTime=type("UnitOfTime", (), {"HOURS": "h"})(),
    UnitOfPressure=type("UnitOfPressure", (), {"HPA": "hPa"})(),
    Platform=type("Platform", (), {
        "FAN": "fan", "NUMBER": "number", "SELECT": "select", "SENSOR": "sensor",
    })(),
)
ha.helpers = types.ModuleType("homeassistant.helpers")
ha.helpers.entity = _make_stub("DeviceInfo", "Entity")
class _DataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls

ha.helpers.update_coordinator = _make_stub("UpdateFailed", DataUpdateCoordinator=_DataUpdateCoordinator)
ha.helpers.entity_platform = _make_stub("AddEntitiesCallback")
ha.helpers.entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")

sensor_mod = types.ModuleType("homeassistant.components.sensor")
sensor_mod.SensorDeviceClass = type("SensorDeviceClass", (), {
    "AQI": "aqi",
    "ATMOSPHERIC_PRESSURE": "atmospheric_pressure",
    "HUMIDITY": "humidity",
    "TEMPERATURE": "temperature",
    "DURATION": "duration",
    "ENUM": "enum",
})()
sensor_mod.SensorEntity = object
sensor_mod.SensorEntityDescription = object
sensor_mod.SensorStateClass = type("SensorStateClass", (), {
    "MEASUREMENT": "measurement",
    "TOTAL_INCREASING": "total_increasing",
})()

fan_mod = _make_stub("FanEntity", "FanEntityDescription", "FanEntityFeature")
number_mod = _make_stub(
    "NumberEntity", "NumberEntityDescription",
    NumberMode=type("NumberMode", (), {"BOX": "box"})(),
    NumberDeviceClass=type("NumberDeviceClass", (), {"TEMPERATURE": "temperature"})(),
)
select_mod = _make_stub("SelectEntity", "SelectEntityDescription")

sys.modules.update({
    "homeassistant": ha,
    "homeassistant.core": ha.core,
    "homeassistant.config_entries": ha.config_entries,
    "homeassistant.exceptions": ha.exceptions,
    "homeassistant.const": ha.const,
    "homeassistant.helpers": ha.helpers,
    "homeassistant.helpers.entity": ha.helpers.entity,
    "homeassistant.helpers.update_coordinator": ha.helpers.update_coordinator,
    "homeassistant.helpers.entity_platform": ha.helpers.entity_platform,
    "homeassistant.helpers.entity_registry": ha.helpers.entity_registry,
    "homeassistant.components": types.ModuleType("homeassistant.components"),
    "homeassistant.components.sensor": sensor_mod,
    "homeassistant.components.fan": fan_mod,
    "homeassistant.components.number": number_mod,
    "homeassistant.components.select": select_mod,
})
