"""Fan platform for ComfoSpot."""
from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import percentage_to_stage, stage_to_percentage
from .const import DOMAIN, MAX_STAGE
from .coordinator import ComfoSpotCoordinator
from .entity import ComfoSpotZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoSpot fans."""
    coordinator: ComfoSpotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ComfoSpotFan(coordinator, addr) for addr in coordinator.data["zones"]
    )


class ComfoSpotFan(ComfoSpotZoneEntity, FanEntity):
    """A ComfoSpot ventilation zone as a fan."""

    _attr_name = None  # use the device/zone name
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = MAX_STAGE

    def __init__(self, coordinator: ComfoSpotCoordinator, addr: int) -> None:
        super().__init__(coordinator, addr)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone{addr}_fan"

    @property
    def _stage(self) -> int:
        speed = self._zone.get("speed")
        return int(round(speed)) if speed is not None else 0

    @property
    def is_on(self) -> bool | None:
        speed = self._zone.get("speed")
        if speed is None:
            return None
        return speed > 0

    @property
    def percentage(self) -> int | None:
        speed = self._zone.get("speed")
        if speed is None:
            return None
        return stage_to_percentage(int(round(speed)))

    async def async_set_percentage(self, percentage: int) -> None:
        stage = percentage_to_stage(percentage)
        await self.coordinator.async_set_stage(self._addr, stage)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if percentage is not None:
            stage = percentage_to_stage(percentage)
        else:
            stage = self._stage or 2
        await self.coordinator.async_set_stage(self._addr, stage)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_stage(self._addr, 0)
        await self.coordinator.async_request_refresh()
