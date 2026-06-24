"""Config flow for ComfoSpot."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .client import ComfoSpot, ComfoSpotError, discover
from .const import DEFAULT_PORT, DOMAIN



class ComfoSpotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ComfoSpot."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Offer the gateway IP found via UDP broadcast as a default.
        suggested_host = ""
        if user_input is None:
            found = await self.hass.async_add_executor_job(discover)
            if found:
                suggested_host = found[0]

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            api = ComfoSpot(host, port)
            try:
                zones = await self.hass.async_add_executor_job(api.test_connection)
            except (ComfoSpotError, OSError):
                errors["base"] = "cannot_connect"
            else:
                await self.hass.async_add_executor_job(api.close)
                title = "ComfoSpot"
                if len(zones) == 1:
                    title = f"ComfoSpot ({next(iter(zones.values()))})"
                return self.async_create_entry(title=title, data={
                    CONF_HOST: host,
                    CONF_PORT: port,
                })

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=suggested_host): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        })
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
