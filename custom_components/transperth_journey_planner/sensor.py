"""Sensors for Transperth Journey Planner."""

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TransperthJourneyCoordinator

_LOGGER = logging.getLogger(__name__)

# Sensor descriptions for each journey option
JOURNEY_OPTION_SENSOR = SensorEntityDescription(
    key="journey_option",
    name="Journey Option",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sensors."""
    coordinator: TransperthJourneyCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    sensors: list[TransperthJourneySensor] = []

    # Create sensors for each route
    for route_name in coordinator.routes.keys():
        # Create a sensor for each journey option (up to 5 options)
        for option_index in range(1, 6):  # Options 1-5
            sensors.append(
                TransperthJourneySensor(coordinator, route_name, option_index)
            )

    async_add_entities(sensors)


class TransperthJourneySensor(CoordinatorEntity, SensorEntity):
    """Implementation of a journey option sensor."""

    def __init__(
        self,
        coordinator: TransperthJourneyCoordinator,
        route_name: str,
        option_index: int,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._route_name = route_name
        self._option_index = option_index
        self._attr_unique_id = f"{DOMAIN}_{route_name}_option_{option_index}"
        self._attr_name = f"Transperth {route_name} Option {option_index}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            name=f"Transperth Journey Planner - {self._route_name}",
            manufacturer="Transperth",
            model="Journey Planner",
            identifiers={(DOMAIN, f"{self._route_name}")},
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the entity."""
        if not self.coordinator.data or not self.coordinator.data.routes:
            return None

        route_data = self.coordinator.data.routes.get(self._route_name)
        if not route_data or not route_data.options:
            return None

        # Get the specific option (index is 1-based, list is 0-based)
        option_idx = self._option_index - 1
        if option_idx >= len(route_data.options):
            return None

        option = route_data.options[option_idx]
        return f"{option.leave_time} → {option.arrive_time}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes."""
        attrs: dict[str, Any] = {
            "route_name": self._route_name,
            "option_index": self._option_index,
        }

        if not self.coordinator.data or not self.coordinator.data.routes:
            return attrs

        route_data = self.coordinator.data.routes.get(self._route_name)
        if not route_data or not route_data.options:
            return attrs

        option_idx = self._option_index - 1
        if option_idx >= len(route_data.options):
            return attrs

        option = route_data.options[option_idx]

        attrs.update(
            {
                "leave_time": option.leave_time,
                "arrive_time": option.arrive_time,
                "travel_time": option.travel_time,
                "from_location": route_data.from_location,
                "to_location": route_data.to_location,
                "date": route_data.date,
                "time": route_data.time,
                "legs": [
                    {
                        "type": leg.type,
                        "description": leg.description,
                        "service_code": leg.service_code,
                    }
                    for leg in option.legs
                ],
                "leg_count": len(option.legs),
            }
        )

        return attrs

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return "mdi:bus"

