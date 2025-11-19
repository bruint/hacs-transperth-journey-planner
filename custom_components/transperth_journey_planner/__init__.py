"""Transperth Journey Planner integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import voluptuous as vol

from .const import DOMAIN
from .coordinator import TransperthJourneyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


@dataclass
class RuntimeData:
    """Class to hold runtime data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Transperth Journey Planner from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Initialize the coordinator that manages data updates
    coordinator = TransperthJourneyCoordinator(hass, config_entry)

    # Perform an initial data load
    await coordinator.async_config_entry_first_refresh()

    # Initialize a listener for config flow options changes
    cancel_update_listener = config_entry.add_update_listener(_async_update_listener)

    # Add the coordinator and update listener to hass data
    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(
        coordinator, cancel_update_listener
    )

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Register services (only once, not per config entry)
    if DOMAIN not in hass.data or "services_registered" not in hass.data[DOMAIN]:
        async def async_refresh_data(call: ServiceCall) -> None:
            """Service to refresh journey data for all routes or a specific route."""
            route_name = call.data.get("route_name")
            config_entry_id = call.data.get("config_entry_id")
            
            # Get all coordinators
            coordinators: list[TransperthJourneyCoordinator] = []
            if config_entry_id:
                # Refresh specific config entry
                if config_entry_id in hass.data.get(DOMAIN, {}):
                    coordinators.append(hass.data[DOMAIN][config_entry_id].coordinator)
            else:
                # Refresh all config entries
                for entry_id, runtime_data in hass.data.get(DOMAIN, {}).items():
                    if isinstance(runtime_data, RuntimeData):
                        coordinators.append(runtime_data.coordinator)
            
            if not coordinators:
                _LOGGER.warning("No Transperth Journey Planner config entries found")
                return
            
            for coordinator in coordinators:
                if route_name:
                    # Refresh specific route
                    _LOGGER.info("Refreshing data for route: %s", route_name)
                    if route_name in coordinator.routes:
                        await coordinator.async_request_refresh()
                    else:
                        _LOGGER.warning("Route '%s' not found in coordinator", route_name)
                else:
                    # Refresh all routes for this coordinator
                    _LOGGER.info("Refreshing data for all routes")
                    await coordinator.async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            "refresh",
            async_refresh_data,
            schema=vol.Schema(
                {
                    vol.Optional("route_name"): cv.string,
                    vol.Optional("config_entry_id"): cv.string,
                }
            ),
        )
        # Mark services as registered
        hass.data.setdefault(DOMAIN, {})["services_registered"] = True

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle config options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Remove the config options update listener
    hass.data[DOMAIN][config_entry.entry_id].cancel_update_listener()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Remove the config entry from the hass data object
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok

