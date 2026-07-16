"""Coordinator: récupère la liste des .ics puis les télécharge et les parse."""
from __future__ import annotations

import asyncio
from datetime import date
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CALENDAR_PAGE_URL, CALENDAR_TYPES, DOMAIN, UPDATE_INTERVAL
from .ics_parser import HolidayEvent, find_ics_urls, merge_and_sort, parse_ics

_LOGGER = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 20
_STORE_VERSION = 1


def _events_to_list(events: list[HolidayEvent]) -> list[dict]:
    return [
        {"summary": e.summary, "start": e.start.isoformat(), "end": e.end.isoformat()}
        for e in events
    ]


def _list_to_events(data: list[dict]) -> list[HolidayEvent]:
    events = []
    for item in data:
        try:
            events.append(
                HolidayEvent(
                    summary=item["summary"],
                    start=date.fromisoformat(item["start"]),
                    end=date.fromisoformat(item["end"]),
                )
            )
        except (KeyError, ValueError) as err:
            _LOGGER.debug("Entrée de cache ignorée (invalide) : %s – %s", item, err)
    return events


class WallonieSchoolHolidaysCoordinator(DataUpdateCoordinator[list[HolidayEvent]]):
    """Télécharge les .ics officiels et les fusionne avec le cache HA.

    Le cache persistant (Store) garantit que les événements déjà récupérés
    ne disparaissent pas quand le site retire un ancien calendrier (ex : le
    .ics 2025-2026 supprimé en juillet alors que les grandes vacances y étaient).
    """

    def __init__(self, hass: HomeAssistant, calendar_type: str) -> None:
        self.calendar_type = calendar_type
        self._filename_pattern = CALENDAR_TYPES[calendar_type]
        self._store: Store = Store(hass, _STORE_VERSION, f"{DOMAIN}.{calendar_type}")
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{calendar_type}",
            update_interval=UPDATE_INTERVAL,
        )

    # ------------------------------------------------------------------
    # Cache persistant
    # ------------------------------------------------------------------

    async def _load_cache(self) -> list[HolidayEvent]:
        try:
            raw = await self._store.async_load()
            if not raw or "events" not in raw:
                return []
            events = _list_to_events(raw["events"])
            _LOGGER.debug("Cache chargé : %d événements", len(events))
            return events
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Impossible de lire le cache : %s", err)
            return []

    async def _save_cache(self, events: list[HolidayEvent]) -> None:
        try:
            await self._store.async_save({"events": _events_to_list(events)})
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Impossible de sauvegarder le cache : %s", err)

    # ------------------------------------------------------------------
    # Mise à jour principale
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> list[HolidayEvent]:
        session = async_get_clientsession(self.hass)
        today = date.today()

        # 1. Charger le cache existant
        cached_events = await self._load_cache()

        # 2. Scraper la page officielle pour trouver les .ics actuellement listés
        fresh_events: list[HolidayEvent] = []
        try:
            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(CALENDAR_PAGE_URL) as resp:
                    resp.raise_for_status()
                    page_html = await resp.text()

            ics_urls = find_ics_urls(page_html, self._filename_pattern)
            if not ics_urls:
                _LOGGER.warning(
                    "Aucun fichier .ics trouvé sur la page pour '%s'. "
                    "Le site a peut-être changé de format. On utilise le cache.",
                    self.calendar_type,
                )
            else:
                _LOGGER.debug("Fichiers .ics trouvés : %s", ics_urls)
                for url in ics_urls:
                    try:
                        async with asyncio.timeout(_REQUEST_TIMEOUT):
                            async with session.get(url) as resp:
                                resp.raise_for_status()
                                raw = await resp.text()
                        fresh_events.extend(parse_ics(raw))
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.warning("Échec de récupération %s : %s", url, err)

        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Impossible de contacter la page officielle : %s. On utilise le cache.", err
            )

        # 3. Fusionner : événements frais + événements du cache qui sont
        #    encore dans le futur (ou en cours) et absents des données fraîches.
        #
        #    Concrètement : si le site a retiré un .ics (ex : grandes vacances),
        #    l'événement reste dans le cache et continue à s'afficher dans HA.
        #    On ne garde du cache que ce qui est futur/en cours pour éviter
        #    d'accumuler des années de données périmées.
        fresh_keys = {(e.summary, e.start, e.end) for e in fresh_events}
        cache_complement = [
            e for e in cached_events
            if e.end >= today and (e.summary, e.start, e.end) not in fresh_keys
        ]

        if cache_complement:
            _LOGGER.debug(
                "%d événement(s) conservé(s) depuis le cache (absents du site)",
                len(cache_complement),
            )

        merged = merge_and_sort(fresh_events + cache_complement)

        if not merged:
            raise UpdateFailed(
                "Aucun événement disponible (ni depuis le web, ni depuis le cache)."
            )

        # 4. Sauvegarder le résultat (frais + complément cache) pour la prochaine fois
        await self._save_cache(merged)

        return merged
