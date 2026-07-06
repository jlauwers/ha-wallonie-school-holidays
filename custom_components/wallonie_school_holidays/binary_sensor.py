"""Binary sensor: vrai si la date du jour tombe dans un congé scolaire."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, CALENDAR_TYPE_NAMES, DOMAIN
from .coordinator import WallonieSchoolHolidaysCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WallonieSchoolHolidaysCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WallonieSchoolHolidayTodaySensor(coordinator, entry)])


class WallonieSchoolHolidayTodaySensor(
    CoordinatorEntity[WallonieSchoolHolidaysCoordinator], BinarySensorEntity
):
    """'on' si aujourd'hui est un jour de congé scolaire (ou jour férié/congé)."""

    _attr_has_entity_name = True
    _attr_translation_key = "school_holiday_today"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: WallonieSchoolHolidaysCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_today"
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
    def is_on(self) -> bool:
        events = self.coordinator.data or []
        today = dt_util.now().date()
        return any(event.start <= today < event.end for event in events)

    @property
    def extra_state_attributes(self) -> dict:
        events = self.coordinator.data or []
        today = dt_util.now().date()
        matching = [event.summary for event in events if event.start <= today < event.end]
        return {"label": matching[0] if matching else None}
