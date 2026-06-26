"""Sensor platform for ComfoSpot."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ComfoSpotCoordinator
from .entity import ComfoSpotEntity, ComfoSpotZoneEntity


@dataclass(frozen=True, kw_only=True)
class ComfoSpotZoneSensorDescription(SensorEntityDescription):
    """Describes a per-zone sensor."""

    value_fn: Callable[[dict], float | None]


ZONE_SENSORS: tuple[ComfoSpotZoneSensorDescription, ...] = (
    ComfoSpotZoneSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda z: z.get("temperature"),
    ),
    ComfoSpotZoneSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda z: z.get("humidity"),
    ),
    ComfoSpotZoneSensorDescription(
        key="run_hours",
        translation_key="run_hours",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda z: z.get("run_hours"),
    ),
)


@dataclass(frozen=True, kw_only=True)
class ComfoSpotSystemSensorDescription(SensorEntityDescription):
    """Describes a system-wide sensor."""

    value_fn: Callable[[dict], float | int | None]


SYSTEM_SENSORS: tuple[ComfoSpotSystemSensorDescription, ...] = (
    ComfoSpotSystemSensorDescription(
        key="co2",
        translation_key="co2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.get("co2"),
    ),
    ComfoSpotSystemSensorDescription(
        key="devices",
        translation_key="devices",
        icon="mdi:fan",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.get("devices"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoSpot sensors."""
    coordinator: ComfoSpotCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for addr in coordinator.data["zones"]:
        for desc in ZONE_SENSORS:
            entities.append(ComfoSpotZoneSensor(coordinator, addr, desc))
    for desc in SYSTEM_SENSORS:
        entities.append(ComfoSpotSystemSensor(coordinator, desc))
    async_add_entities(entities)


class ComfoSpotZoneSensor(ComfoSpotZoneEntity, SensorEntity):
    """A per-zone sensor."""

    entity_description: ComfoSpotZoneSensorDescription

    def __init__(
        self,
        coordinator: ComfoSpotCoordinator,
        addr: int,
        description: ComfoSpotZoneSensorDescription,
    ) -> None:
        super().__init__(coordinator, addr)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone{addr}_{description.key}"

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self._zone)


class ComfoSpotSystemSensor(ComfoSpotEntity, SensorEntity):
    """A system-wide sensor."""

    entity_description: ComfoSpotSystemSensorDescription

    def __init__(
        self,
        coordinator: ComfoSpotCoordinator,
        description: ComfoSpotSystemSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_system_{description.key}"

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data["system"])
