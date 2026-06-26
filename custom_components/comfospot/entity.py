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

    @property
    def device_info(self) -> DeviceInfo:
        firmware = self.coordinator.data.get("system", {}).get("firmware")
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="ComfoSpot",
            manufacturer="Zehnder / getair",
            model="ComfoSpot 55",
            sw_version=firmware,
        )


class ComfoSpotZoneEntity(ComfoSpotEntity):
    """Base entity bound to a single ventilation zone (its own sub-device)."""

    def __init__(self, coordinator: ComfoSpotCoordinator, addr: int) -> None:
        super().__init__(coordinator)
        self._addr = addr

    @property
    def device_info(self) -> DeviceInfo:
        zone_name = self._zone.get("name") or f"Zone {self._addr}"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.entry.entry_id}_zone{self._addr}")},
            name=zone_name,
            manufacturer="Zehnder / getair",
            model="ComfoSpot 55",
            via_device=(DOMAIN, self.coordinator.entry.entry_id),
        )

    @property
    def _zone(self) -> dict:
        return self.coordinator.data["zones"].get(self._addr, {})

    @property
    def available(self) -> bool:
        return super().available and self._addr in self.coordinator.data["zones"]
