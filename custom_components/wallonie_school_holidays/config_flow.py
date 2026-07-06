"""Config flow pour Congés scolaires FW-B."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CALENDAR_TYPE_NAMES,
    CONF_CALENDAR_TYPE,
    DEFAULT_CALENDAR_TYPE,
    DOMAIN,
)


class WallonieSchoolHolidaysConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gère la configuration via l'UI (Paramètres > Appareils et services)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            calendar_type = user_input[CONF_CALENDAR_TYPE]

            # Une seule instance par type de calendrier
            await self.async_set_unique_id(f"{DOMAIN}_{calendar_type}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=CALENDAR_TYPE_NAMES[calendar_type],
                data={CONF_CALENDAR_TYPE: calendar_type},
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CALENDAR_TYPE, default=DEFAULT_CALENDAR_TYPE
                ): vol.In(CALENDAR_TYPE_NAMES)
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
