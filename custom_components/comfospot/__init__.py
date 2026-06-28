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

# Entity keys that were removed in previous versions and must be cleaned up.
_REMOVED_UNIQUE_ID_SUFFIXES = ("_system_devices",)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ComfoSpot from a config entry."""
    _remove_stale_entities(hass, entry)
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
        if any(uid.endswith(suffix) for suffix in _REMOVED_UNIQUE_ID_SUFFIXES):
            registry.async_remove(entity_entry.entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ComfoSpotCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.api.close)
    return unload_ok
