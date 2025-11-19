"""Buttons for Transperth Journey Planner."""

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TransperthJourneyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Buttons."""
    coordinator: TransperthJourneyCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    buttons: list[TransperthRefreshButton] = []

    # Create a refresh button for each route
    for route_name in coordinator.routes.keys():
        buttons.append(
            TransperthRefreshButton(coordinator, route_name, config_entry.entry_id)
        )

    async_add_entities(buttons)


class TransperthRefreshButton(CoordinatorEntity, ButtonEntity):
    """Implementation of a refresh button for a route."""

    def __init__(
        self,
        coordinator: TransperthJourneyCoordinator,
        route_name: str,
        config_entry_id: str,
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator)
        self._route_name = route_name
        self._config_entry_id = config_entry_id
        self._attr_unique_id = f"{DOMAIN}_{route_name}_refresh"
        self._attr_name = f"Refresh {route_name}"

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
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Refresh button pressed for route: %s", self._route_name)
        await self.coordinator.async_request_refresh()

