"""The ComfoSpot integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .client import ComfoSpot, ComfoSpotError
from .const import DEFAULT_PORT, DOMAIN
from .coordinator import ComfoSpotCoordinator

PLATFORMS: list[Platform] = [Platform.FAN, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]

import re as _re

# Patterns matching unique_ids of entities removed in previous versions.
_STALE_UID_PATTERNS = (
    _re.compile(r"_system_devices$"),        # removed in 0.1.5: always-3 BLE mesh counter
    _re.compile(r"_zone\d+_run_hours$"),     # removed in 0.1.5: moved to system sensor
)

# unique_ids renamed in 0.1.8 once the sensors were identified: 0x1041 is
# barometric pressure in hPa (not CO2) and 0x1043 is the BSEC air quality index.
_UID_MIGRATIONS = {
    "_system_co2": "_system_pressure",
    "_system_unknown_1043": "_system_air_quality",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ComfoSpot from a config entry."""
    _remove_stale_entities(hass, entry)
    _migrate_unique_ids(hass, entry)
    api = ComfoSpot(entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT))
    coordinator = ComfoSpotCoordinator(hass, entry, api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await hass.async_add_executor_job(api.close)
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entity registry entries that were deleted in a previous version."""
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = entity_entry.unique_id or ""
        if any(p.search(uid) for p in _STALE_UID_PATTERNS):
            registry.async_remove(entity_entry.entity_id)


def _migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename unique_ids of entities that were re-identified, keeping history."""
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = entity_entry.unique_id or ""
        for old, new in _UID_MIGRATIONS.items():
            if not uid.endswith(old):
                continue
            new_uid = uid[: -len(old)] + new
            if registry.async_get_entity_id("sensor", DOMAIN, new_uid) is None:
                registry.async_update_entity(
                    entity_entry.entity_id, new_unique_id=new_uid
                )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ComfoSpotCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.api.close)
    return unload_ok
