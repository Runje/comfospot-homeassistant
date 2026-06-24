"""Number platform for ComfoSpot (target temperature)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ComfoSpotCoordinator
from .entity import ComfoSpotZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoSpot target-temperature numbers."""
    coordinator: ComfoSpotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ComfoSpotTargetTemp(coordinator, addr) for addr in coordinator.data["zones"]
    )


class ComfoSpotTargetTemp(ComfoSpotZoneEntity, NumberEntity):
    """Target temperature for a ventilation zone."""

    _attr_translation_key = "target_temperature"
    _attr_device_class = "temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 15.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ComfoSpotCoordinator, addr: int) -> None:
        super().__init__(coordinator, addr)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone{addr}_target_temp"

    @property
    def native_value(self) -> float | None:
        return self._zone.get("target_temp")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_target_temp(self._addr, value)
        await self.coordinator.async_request_refresh()
