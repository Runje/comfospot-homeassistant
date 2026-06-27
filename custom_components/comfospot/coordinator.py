"""DataUpdateCoordinator for ComfoSpot."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ComfoSpot, ComfoSpotError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=15)


class ComfoSpotCoordinator(DataUpdateCoordinator[dict]):
    """Polls the ComfoSpot and keeps the Flake connection alive."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: ComfoSpot) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self.api.update)
        except ComfoSpotError as err:
            raise UpdateFailed(str(err)) from err
        except OSError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

    async def async_set_stage(self, addr: int, stage: int) -> None:
        """Set the fan stage for a zone (executor)."""
        await self.hass.async_add_executor_job(self.api.set_stage, addr, stage)

    async def async_set_mode(self, addr: int, mode: int) -> None:
        """Set the ventilation mode for a zone (executor)."""
        await self.hass.async_add_executor_job(self.api.set_mode, addr, mode)

    async def async_set_target_temp(self, addr: int, temp: float) -> None:
        """Set the target temperature for a zone (executor)."""
        await self.hass.async_add_executor_job(self.api.set_target_temp, addr, temp)
