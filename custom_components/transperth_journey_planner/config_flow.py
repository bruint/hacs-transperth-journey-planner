"""Config flow for Transperth Journey Planner integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
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
    MIN_SCAN_INTERVAL,
    DEPARTURE_OPTIONS,
    WALK_SPEEDS,
    TRANSPORT_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class TransperthJourneyPlannerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Transperth Journey Planner."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return TransperthJourneyPlannerOptionsFlowHandler(config_entry)

    def _parse_journey_url(self, url: str) -> dict[str, Any] | None:
        """Parse a Transperth journey planner URL and extract parameters."""
        try:
            parsed = urlparse(url)
            if "Journey-Planner" not in parsed.path:
                return None
            
            params = parse_qs(parsed.query)
            if not params:
                return None
            
            # Extract parameters
            result: dict[str, Any] = {}
            
            if "from" in params:
                result[CONF_FROM] = params["from"][0]
            if "fromtype" in params:
                result[CONF_FROM_TYPE] = params["fromtype"][0]
            if "fromposition" in params:
                result[CONF_FROM_POSITION] = params["fromposition"][0]
            if "fromlocality" in params:
                result[CONF_FROM_LOCALITY] = params["fromlocality"][0]
            if "to" in params:
                result[CONF_TO] = params["to"][0]
            if "totype" in params:
                result[CONF_TO_TYPE] = params["totype"][0]
            if "toposition" in params:
                result[CONF_TO_POSITION] = params["toposition"][0]
            if "tolocality" in params:
                result[CONF_TO_LOCALITY] = params["tolocality"][0]
            if "date" in params:
                result[CONF_DATE] = params["date"][0]
            if "time" in params:
                result[CONF_TIME] = params["time"][0]
            if "departureOption" in params:
                dep_option = params["departureOption"][0]
                # Map to our internal format
                if dep_option == "LeaveAfter":
                    result[CONF_DEPARTURE_OPTION] = "leave_after"
                elif dep_option == "ArriveBy":
                    result[CONF_DEPARTURE_OPTION] = "arrive_by"
                elif dep_option == "EarliestTrip":
                    result[CONF_DEPARTURE_OPTION] = "earliest_trip"
                elif dep_option == "LastTrip":
                    result[CONF_DEPARTURE_OPTION] = "last_trip"
            
            # Transport options
            transport_opts = []
            if "bus" in params:
                transport_opts.append("bus")
            if "train" in params:
                transport_opts.append("train")
            if "ferry" in params:
                transport_opts.append("ferry")
            if "schoolbus" in params:
                transport_opts.append("school_bus")
            if transport_opts:
                result["_transport_options"] = transport_opts
            
            # Walk speed
            if "walkSpeed" in params:
                walk_speed = params["walkSpeed"][0].lower()
                if walk_speed in WALK_SPEEDS:
                    result[CONF_WALK_SPEED] = walk_speed
            
            # Max connections
            if "maxConnections" in params:
                max_conn = params["maxConnections"][0]
                if max_conn != "Direct":
                    try:
                        result[CONF_MAX_CONNECTIONS] = int(max_conn)
                    except ValueError:
                        pass
            
            # Max walking distance
            if "maxWalkingDistance" in params:
                result[CONF_MAX_WALKING_DISTANCE] = params["maxWalkingDistance"][0]
            
            return result if result else None
        except Exception as e:
            _LOGGER.error("Error parsing journey URL: %s", e)
            return None

    def _get_date_from_selection(self, date_selection: str) -> str:
        """Convert date selection to actual date string."""
        today = datetime.now()
        if date_selection == "today":
            return today.strftime("%Y-%m-%d")
        elif date_selection == "tomorrow":
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")
        else:
            # Custom date - should be in YYYY-MM-DD format
            return date_selection

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - offer quick config or manual."""
        # Initialize routes if not already done
        if not hasattr(self, '_routes'):
            self._routes = {}
        
        if user_input is not None:
            if user_input.get("config_method") == "url":
                return await self.async_step_quick_config()
            else:
                return await self.async_step_add_route()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("config_method", default="manual"): vol.In({
                    "manual": "Manual Configuration",
                    "url": "Quick Config from URL"
                })
            })
        )

    async def async_step_quick_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle quick config from URL."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            url = user_input.get("journey_url", "").strip()
            if not url:
                errors["journey_url"] = "required"
            else:
                parsed = self._parse_journey_url(url)
                if not parsed:
                    errors["journey_url"] = "invalid_url"
                else:
                    # Store parsed data and move to route name step
                    self._parsed_url_data = parsed
                    return await self.async_step_add_route()
        
        return self.async_show_form(
            step_id="quick_config",
            data_schema=vol.Schema({
                vol.Required("journey_url"): str,
            }),
            description="Paste a Transperth Journey Planner URL to automatically fill in the route details.",
            errors=errors,
        )

    async def async_step_add_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a route."""
        errors: dict[str, str] = {}
        
        # Get parsed URL data if available
        parsed_data = getattr(self, '_parsed_url_data', {})

        if user_input is not None:
            route_name = user_input.get("route_name", "").strip()
            if not route_name:
                errors["route_name"] = "required"
            elif route_name in self._routes:
                errors["route_name"] = "duplicate"
            else:
                # Get date from selection - store the selection for dynamic dates
                date_selection = user_input.get("date_selection", "today")
                if date_selection == "custom":
                    custom_date = user_input.get("custom_date", "")
                    stored_date = custom_date if custom_date else "today"
                else:
                    # Store "today" or "tomorrow" for dynamic resolution
                    stored_date = date_selection
                
                # Store route configuration
                self._routes[route_name] = {
                    CONF_FROM: user_input.get(CONF_FROM) or parsed_data.get(CONF_FROM, ""),
                    CONF_FROM_TYPE: user_input.get(CONF_FROM_TYPE) or parsed_data.get(CONF_FROM_TYPE, "psma_addresses"),
                    CONF_FROM_POSITION: user_input.get(CONF_FROM_POSITION) or parsed_data.get(CONF_FROM_POSITION, ""),
                    CONF_FROM_LOCALITY: user_input.get(CONF_FROM_LOCALITY) or parsed_data.get(CONF_FROM_LOCALITY, ""),
                    CONF_TO: user_input.get(CONF_TO) or parsed_data.get(CONF_TO, ""),
                    CONF_TO_TYPE: user_input.get(CONF_TO_TYPE) or parsed_data.get(CONF_TO_TYPE, "psma_addresses"),
                    CONF_TO_POSITION: user_input.get(CONF_TO_POSITION) or parsed_data.get(CONF_TO_POSITION, ""),
                    CONF_TO_LOCALITY: user_input.get(CONF_TO_LOCALITY) or parsed_data.get(CONF_TO_LOCALITY, ""),
                    CONF_DATE: stored_date,
                    CONF_TIME: user_input.get(CONF_TIME) or parsed_data.get(CONF_TIME, ""),
                    CONF_DEPARTURE_OPTION: user_input.get(
                        CONF_DEPARTURE_OPTION
                    ) or parsed_data.get(CONF_DEPARTURE_OPTION, "leave_after"),
                    CONF_TRANSPORT_OPTIONS: (
                        [
                            opt
                            for opt in TRANSPORT_OPTIONS
                            if user_input.get(f"transport_{opt}", False)
                        ]
                        if any(user_input.get(f"transport_{opt}", False) for opt in TRANSPORT_OPTIONS)
                        else (
                            parsed_data.get("_transport_options", [])
                            if "_transport_options" in parsed_data
                            else ["bus", "train"]
                        )
                    ),
                    CONF_WALK_SPEED: user_input.get(CONF_WALK_SPEED) or parsed_data.get(CONF_WALK_SPEED, "normal"),
                    CONF_MAX_CONNECTIONS: (
                        int(user_input[CONF_MAX_CONNECTIONS])
                        if user_input.get(CONF_MAX_CONNECTIONS)
                        and str(user_input.get(CONF_MAX_CONNECTIONS, "")).strip()
                        else parsed_data.get(CONF_MAX_CONNECTIONS)
                    ),
                    CONF_MAX_WALKING_DISTANCE: (
                        user_input.get(CONF_MAX_WALKING_DISTANCE) or parsed_data.get(CONF_MAX_WALKING_DISTANCE)
                    ),
                }
                
                # Clear parsed data after use
                if hasattr(self, '_parsed_url_data'):
                    delattr(self, '_parsed_url_data')

                # Ask if user wants to add another route
                return await self.async_step_add_another()

        # Determine defaults from parsed data
        today_str = datetime.now().strftime("%Y-%m-%d")
        default_date_selection = "today"
        if parsed_data.get(CONF_DATE):
            if parsed_data[CONF_DATE] == today_str:
                default_date_selection = "today"
            elif parsed_data[CONF_DATE] == (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"):
                default_date_selection = "tomorrow"
            else:
                default_date_selection = "custom"

        data_schema = vol.Schema(
            {
                vol.Required(
                    "route_name",
                    description={"suggested_value": parsed_data.get("route_name", "")}
                ): str,
                vol.Required(
                    CONF_FROM,
                    description={"suggested_value": parsed_data.get(CONF_FROM, "")}
                ): str,
                vol.Optional(
                    CONF_FROM_TYPE,
                    default=parsed_data.get(CONF_FROM_TYPE, "psma_addresses"),
                    description={"suggested_value": parsed_data.get(CONF_FROM_TYPE, "")}
                ): str,
                vol.Required(
                    CONF_FROM_POSITION,
                    description={"suggested_value": parsed_data.get(CONF_FROM_POSITION, "")}
                ): str,
                vol.Optional(
                    CONF_FROM_LOCALITY,
                    default=parsed_data.get(CONF_FROM_LOCALITY, ""),
                    description={"suggested_value": parsed_data.get(CONF_FROM_LOCALITY, "")}
                ): str,
                vol.Required(
                    CONF_TO,
                    description={"suggested_value": parsed_data.get(CONF_TO, "")}
                ): str,
                vol.Optional(
                    CONF_TO_TYPE,
                    default=parsed_data.get(CONF_TO_TYPE, "psma_addresses"),
                    description={"suggested_value": parsed_data.get(CONF_TO_TYPE, "")}
                ): str,
                vol.Required(
                    CONF_TO_POSITION,
                    description={"suggested_value": parsed_data.get(CONF_TO_POSITION, "")}
                ): str,
                vol.Optional(
                    CONF_TO_LOCALITY,
                    default=parsed_data.get(CONF_TO_LOCALITY, ""),
                    description={"suggested_value": parsed_data.get(CONF_TO_LOCALITY, "")}
                ): str,
                vol.Required(
                    "date_selection",
                    default=default_date_selection
                ): vol.In({
                    "today": "Today",
                    "tomorrow": "Tomorrow",
                    "custom": "Custom Date"
                }),
                vol.Optional(
                    "custom_date",
                    default=parsed_data.get(CONF_DATE, ""),
                    description={"suggested_value": parsed_data.get(CONF_DATE, "")}
                ): str,
                vol.Optional(
                    CONF_TIME,
                    default=parsed_data.get(CONF_TIME, ""),
                    description={"suggested_value": parsed_data.get(CONF_TIME, "")}
                ): str,
                vol.Optional(
                    CONF_DEPARTURE_OPTION,
                    default=parsed_data.get(CONF_DEPARTURE_OPTION, "leave_after")
                ): vol.In({
                    "leave_after": "Leave After",
                    "arrive_by": "Arrive By",
                    "earliest_trip": "Earliest Trip",
                    "last_trip": "Last Trip"
                }),
                vol.Optional(
                    "transport_bus",
                    default=("bus" in parsed_data.get("_transport_options", ["bus", "train"]) if "_transport_options" in parsed_data else True)
                ): bool,
                vol.Optional(
                    "transport_train",
                    default=("train" in parsed_data.get("_transport_options", ["bus", "train"]) if "_transport_options" in parsed_data else True)
                ): bool,
                vol.Optional(
                    "transport_ferry",
                    default=("ferry" in parsed_data.get("_transport_options", []) if "_transport_options" in parsed_data else False)
                ): bool,
                vol.Optional(
                    "transport_school_bus",
                    default=("school_bus" in parsed_data.get("_transport_options", []) if "_transport_options" in parsed_data else False)
                ): bool,
                vol.Optional(
                    CONF_WALK_SPEED,
                    default=parsed_data.get(CONF_WALK_SPEED, "normal")
                ): vol.In({
                    "slow": "Slow",
                    "normal": "Normal",
                    "fast": "Fast"
                }),
                vol.Optional(
                    CONF_MAX_CONNECTIONS,
                    default=str(parsed_data.get(CONF_MAX_CONNECTIONS, "")) if parsed_data.get(CONF_MAX_CONNECTIONS) else "",
                    description={"suggested_value": str(parsed_data.get(CONF_MAX_CONNECTIONS, "")) if parsed_data.get(CONF_MAX_CONNECTIONS) else ""}
                ): str,
                vol.Optional(
                    CONF_MAX_WALKING_DISTANCE,
                    default=parsed_data.get(CONF_MAX_WALKING_DISTANCE, ""),
                    description={"suggested_value": parsed_data.get(CONF_MAX_WALKING_DISTANCE, "")}
                ): str,
            }
        )

        return self.async_show_form(
            step_id="add_route", data_schema=data_schema, errors=errors
        )

    async def async_step_add_another(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask if user wants to add another route."""
        if user_input is not None:
            if user_input.get("add_another", False):
                return await self.async_step_add_route()
            else:
                # Validate we have at least one route
                if not self._routes:
                    return await self.async_step_add_route()
                # Finish and create entry
                return self.async_create_entry(
                    title="Transperth Journey Planner",
                    data={"routes": self._routes},
                )

        routes_list = ", ".join(self._routes.keys()) if self._routes else "None"
        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema(
                {
                    vol.Required("add_another", default=False): bool,
                }
            ),
            description_placeholders={
                "routes": routes_list,
                "route_count": str(len(self._routes)),
            },
        )


class TransperthJourneyPlannerOptionsFlowHandler(OptionsFlow):
    """Handles the options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            options = self.config_entry.options | user_input
            return self.async_create_entry(title="", data=options)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): (
                    vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL))
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

