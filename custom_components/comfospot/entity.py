"""Base entities for ComfoSpot."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ComfoSpotCoordinator


class ComfoSpotEntity(CoordinatorEntity[ComfoSpotCoordinator]):
    """Base entity tied to the ComfoSpot gateway (hub device)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ComfoSpotCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="ComfoSpot",
            manufacturer="Zehnder / getair",
            model="ComfoSpot 55",
        )


class ComfoSpotZoneEntity(ComfoSpotEntity):
    """Base entity bound to a single ventilation zone (its own sub-device)."""

    def __init__(self, coordinator: ComfoSpotCoordinator, addr: int) -> None:
        super().__init__(coordinator)
        self._addr = addr
        zone_name = self._zone.get("name") or f"Zone {addr}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_zone{addr}")},
            name=zone_name,
            manufacturer="Zehnder / getair",
            model="ComfoSpot 55",
            via_device=(DOMAIN, coordinator.entry.entry_id),
        )

    @property
    def _zone(self) -> dict:
        return self.coordinator.data["zones"].get(self._addr, {})

    @property
    def available(self) -> bool:
        return super().available and self._addr in self.coordinator.data["zones"]
