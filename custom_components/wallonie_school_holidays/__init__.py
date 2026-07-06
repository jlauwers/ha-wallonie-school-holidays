"""Intégration Congés scolaires en Fédération Wallonie-Bruxelles."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CALENDAR_TYPE, DOMAIN
from .coordinator import WallonieSchoolHolidaysCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration à partir d'une config entry."""
    calendar_type = entry.data[CONF_CALENDAR_TYPE]

    coordinator = WallonieSchoolHolidaysCoordinator(hass, calendar_type)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
