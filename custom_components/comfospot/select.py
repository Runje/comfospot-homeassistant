"""Select platform for ComfoSpot (ventilation mode)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MODES, MODES_INV
from .coordinator import ComfoSpotCoordinator
from .entity import ComfoSpotZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoSpot mode selects."""
    coordinator: ComfoSpotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ComfoSpotModeSelect(coordinator, addr) for addr in coordinator.data["zones"]
    )


class ComfoSpotModeSelect(ComfoSpotZoneEntity, SelectEntity):
    """Ventilation mode selector for a ComfoSpot zone."""

    _attr_translation_key = "ventilation_mode"
    _attr_options = list(MODES.keys())

    def __init__(self, coordinator: ComfoSpotCoordinator, addr: int) -> None:
        super().__init__(coordinator, addr)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone{addr}_mode"

    @property
    def current_option(self) -> str | None:
        raw = self._zone.get("mode")
        if raw is None:
            return None
        return MODES_INV.get(raw & 0x0F)

    async def async_select_option(self, option: str) -> None:
        mode = MODES[option]
        await self.coordinator.async_set_mode(self._addr, mode)
        await self.coordinator.async_request_refresh()
