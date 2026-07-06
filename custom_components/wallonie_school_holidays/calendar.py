"""Plateforme calendar pour les congés scolaires FW-B."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, CALENDAR_TYPE_NAMES, CONF_CALENDAR_TYPE, DOMAIN
from .coordinator import WallonieSchoolHolidaysCoordinator
from .ics_parser import HolidayEvent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Ajoute l'entité calendar pour cette config entry."""
    coordinator: WallonieSchoolHolidaysCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WallonieSchoolHolidaysCalendar(coordinator, entry)])


def _to_calendar_event(event: HolidayEvent) -> CalendarEvent:
    return CalendarEvent(
        start=event.start,
        end=event.end,
        summary=event.summary,
    )


class WallonieSchoolHolidaysCalendar(
    CoordinatorEntity[WallonieSchoolHolidaysCoordinator], CalendarEntity
):
    """Calendrier HA listant les jours fériés et périodes de congé scolaire."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: WallonieSchoolHolidaysCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        calendar_type_label = CALENDAR_TYPE_NAMES.get(
            coordinator.calendar_type, coordinator.calendar_type
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Congés scolaires FW-B – {calendar_type_label}",
            manufacturer="Fédération Wallonie-Bruxelles",
            model="enseignement.be",
            entry_type="service",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Retourne l'événement en cours, ou le prochain à venir."""
        events = self.coordinator.data or []
        now = dt_util.now().date()

        current = None
        upcoming = None
        for event in events:
            if event.start <= now < event.end:
                current = event
                break
            if event.start >= now and (upcoming is None or event.start < upcoming.start):
                upcoming = event

        chosen = current or upcoming
        return _to_calendar_event(chosen) if chosen else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Retourne les événements dans l'intervalle demandé par le frontend HA."""
        events = self.coordinator.data or []
        start = start_date.date()
        end = end_date.date()

        return [
            _to_calendar_event(event)
            for event in events
            if event.start < end and event.end > start
        ]
