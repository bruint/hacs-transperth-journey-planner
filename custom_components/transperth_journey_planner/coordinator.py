"""Transperth Journey Planner integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TransperthAPI, JourneyData
from .const import (
    CONF_FROM,
    CONF_FROM_TYPE,
    CONF_FROM_POSITION,
    CONF_FROM_LOCALITY,
    CONF_TO,
    CONF_TO_TYPE,
    CONF_TO_POSITION,
    CONF_TO_LOCALITY,
    CONF_DATE,
    CONF_TIME,
    CONF_DEPARTURE_OPTION,
    CONF_TRANSPORT_OPTIONS,
    CONF_WALK_SPEED,
    CONF_MAX_CONNECTIONS,
    CONF_MAX_WALKING_DISTANCE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class RouteConfig:
    """Configuration for a journey route."""

    name: str
    from_location: str
    from_type: str
    from_position: str
    from_locality: str
    to_location: str
    to_type: str
    to_position: str
    to_locality: str
    date: str
    time: str
    departure_option: str
    transport_options: list[str]
    walk_speed: str
    max_connections: int | None
    max_walking_distance: str | None


@dataclass
class TransperthJourneyData:
    """Class to hold journey data."""

    routes: dict[str, JourneyData]


class TransperthJourneyCoordinator(DataUpdateCoordinator):
    """Coordinator for Transperth Journey Planner."""

    data: TransperthJourneyData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Get scan interval from options
        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        # Extract route configurations from config entry
        self.routes: dict[str, RouteConfig] = {}
        if "routes" in config_entry.data:
            for route_name, route_data in config_entry.data["routes"].items():
                self.routes[route_name] = RouteConfig(
                    name=route_name,
                    from_location=route_data[CONF_FROM],
                    from_type=route_data.get(CONF_FROM_TYPE, "psma_addresses"),
                    from_position=route_data[CONF_FROM_POSITION],
                    from_locality=route_data.get(CONF_FROM_LOCALITY, ""),
                    to_location=route_data[CONF_TO],
                    to_type=route_data.get(CONF_TO_TYPE, "psma_addresses"),
                    to_position=route_data[CONF_TO_POSITION],
                    to_locality=route_data.get(CONF_TO_LOCALITY, ""),
                    date=route_data.get(CONF_DATE, ""),
                    time=route_data.get(CONF_TIME, ""),
                    departure_option=route_data.get(CONF_DEPARTURE_OPTION, "leave_after"),
                    transport_options=route_data.get(CONF_TRANSPORT_OPTIONS, ["bus", "train"]),
                    walk_speed=route_data.get(CONF_WALK_SPEED, "normal"),
                    max_connections=route_data.get(CONF_MAX_CONNECTIONS),
                    max_walking_distance=route_data.get(CONF_MAX_WALKING_DISTANCE),
                )

        # Initialize DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # Initialize API
        self.api = TransperthAPI()

    def _get_default_date(self) -> str:
        """Get default date in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_default_time(self) -> str:
        """Get default time in HH:MM format."""
        return datetime.now().strftime("%H:%M")

    async def async_update_data(self) -> TransperthJourneyData:
        """Fetch data from API endpoint.

        Returns:
            TransperthJourneyData containing journey data for all routes
        """
        routes_data: dict[str, JourneyData] = {}

        for route_name, route_config in self.routes.items():
            try:
                _LOGGER.debug("Fetching journey data for route: %s", route_name)
                # Use defaults if date/time not provided
                date = route_config.date or self._get_default_date()
                time = route_config.time or self._get_default_time()
                
                journey_data = await self.hass.async_add_executor_job(
                    self.api.get_journey_options,
                    route_config.from_location,
                    route_config.from_type,
                    route_config.from_position,
                    route_config.from_locality,
                    route_config.to_location,
                    route_config.to_type,
                    route_config.to_position,
                    route_config.to_locality,
                    date,
                    time,
                    route_config.departure_option,
                    route_config.transport_options,
                    route_config.walk_speed,
                    route_config.max_connections,
                    route_config.max_walking_distance,
                )
                routes_data[route_name] = journey_data
                _LOGGER.debug(
                    "Found %d journey options for route: %s",
                    len(journey_data.options),
                    route_name,
                )
            except Exception as err:
                _LOGGER.error(
                    "Error fetching journey data for route %s: %s", route_name, err
                )
                # Continue with other routes even if one fails
                continue

        return TransperthJourneyData(routes=routes_data)

