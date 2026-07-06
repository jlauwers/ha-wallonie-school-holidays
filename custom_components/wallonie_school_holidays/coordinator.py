"""Coordinator: récupère la liste des .ics puis les télécharge et les parse."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CALENDAR_PAGE_URL, CALENDAR_TYPES, DOMAIN, UPDATE_INTERVAL
from .ics_parser import HolidayEvent, find_ics_urls, merge_and_sort, parse_ics

_LOGGER = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 20


class WallonieSchoolHolidaysCoordinator(DataUpdateCoordinator[list[HolidayEvent]]):
    """Télécharge la page officielle, retrouve les .ics pertinents, les parse."""

    def __init__(self, hass: HomeAssistant, calendar_type: str) -> None:
        self.calendar_type = calendar_type
        self._filename_pattern = CALENDAR_TYPES[calendar_type]
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{calendar_type}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> list[HolidayEvent]:
        session = async_get_clientsession(self.hass)

        try:
            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(CALENDAR_PAGE_URL) as resp:
                    resp.raise_for_status()
                    page_html = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(
                f"Impossible de charger la page {CALENDAR_PAGE_URL}: {err}"
            ) from err

        ics_urls = find_ics_urls(page_html, self._filename_pattern)
        if not ics_urls:
            raise UpdateFailed(
                "Aucun fichier .ics trouvé sur la page officielle pour le "
                f"type '{self.calendar_type}'. Le site a peut-être changé de format."
            )

        _LOGGER.debug("Fichiers .ics trouvés pour %s: %s", self.calendar_type, ics_urls)

        all_events: list[HolidayEvent] = []
        errors: list[str] = []

        for url in ics_urls:
            try:
                async with asyncio.timeout(_REQUEST_TIMEOUT):
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        raw = await resp.text()
            except Exception as err:  # noqa: BLE001
                errors.append(f"{url}: {err}")
                continue

            try:
                all_events.extend(parse_ics(raw))
            except Exception as err:  # noqa: BLE001
                errors.append(f"{url} (parsing): {err}")

        if not all_events:
            raise UpdateFailed(
                "Aucun événement n'a pu être récupéré. Erreurs: " + "; ".join(errors)
            )

        if errors:
            _LOGGER.warning(
                "Certains calendriers n'ont pas pu être récupérés: %s",
                "; ".join(errors),
            )

        return merge_and_sort(all_events)
