"""Config flow for Transperth Journey Planner integration."""

from __future__ import annotations

import logging
from typing import Any

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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Initialize routes if not already done
        if not hasattr(self, '_routes'):
            self._routes = {}
        # Always start by adding a route
        return await self.async_step_add_route()

    async def async_step_add_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a route."""
        errors: dict[str, str] = {}

        if user_input is not None:
            route_name = user_input.get("route_name", "").strip()
            if not route_name:
                errors["route_name"] = "required"
            elif route_name in self._routes:
                errors["route_name"] = "duplicate"
            else:
                # Store route configuration
                self._routes[route_name] = {
                    CONF_FROM: user_input[CONF_FROM],
                    CONF_FROM_TYPE: user_input.get(CONF_FROM_TYPE, "psma_addresses"),
                    CONF_FROM_POSITION: user_input[CONF_FROM_POSITION],
                    CONF_FROM_LOCALITY: user_input.get(CONF_FROM_LOCALITY, ""),
                    CONF_TO: user_input[CONF_TO],
                    CONF_TO_TYPE: user_input.get(CONF_TO_TYPE, "psma_addresses"),
                    CONF_TO_POSITION: user_input[CONF_TO_POSITION],
                    CONF_TO_LOCALITY: user_input.get(CONF_TO_LOCALITY, ""),
                    CONF_DATE: user_input.get(CONF_DATE, ""),
                    CONF_TIME: user_input.get(CONF_TIME, ""),
                    CONF_DEPARTURE_OPTION: user_input.get(
                        CONF_DEPARTURE_OPTION, "leave_after"
                    ),
                    CONF_TRANSPORT_OPTIONS: (
                        [
                            opt
                            for opt in TRANSPORT_OPTIONS
                            if user_input.get(f"transport_{opt}", False)
                        ]
                        if any(user_input.get(f"transport_{opt}", False) for opt in TRANSPORT_OPTIONS)
                        else ["bus", "train"]  # Default to bus and train if none selected
                    ),
                    CONF_WALK_SPEED: user_input.get(CONF_WALK_SPEED, "normal"),
                    CONF_MAX_CONNECTIONS: (
                        int(user_input[CONF_MAX_CONNECTIONS])
                        if user_input.get(CONF_MAX_CONNECTIONS)
                        and str(user_input.get(CONF_MAX_CONNECTIONS, "")).strip()
                        else None
                    ),
                    CONF_MAX_WALKING_DISTANCE: (
                        user_input.get(CONF_MAX_WALKING_DISTANCE) or None
                    ),
                }

                # Ask if user wants to add another route
                return await self.async_step_add_another()

        data_schema = vol.Schema(
            {
                vol.Required("route_name"): str,
                vol.Required(CONF_FROM): str,
                vol.Optional(CONF_FROM_TYPE, default="psma_addresses"): str,
                vol.Required(CONF_FROM_POSITION): str,
                vol.Optional(CONF_FROM_LOCALITY, default=""): str,
                vol.Required(CONF_TO): str,
                vol.Optional(CONF_TO_TYPE, default="psma_addresses"): str,
                vol.Required(CONF_TO_POSITION): str,
                vol.Optional(CONF_TO_LOCALITY, default=""): str,
                vol.Optional(CONF_DATE, default=""): str,
                vol.Optional(CONF_TIME, default=""): str,
                vol.Optional(
                    CONF_DEPARTURE_OPTION, default="leave_after"
                ): vol.In(DEPARTURE_OPTIONS),
                vol.Optional("transport_bus", default=True): bool,
                vol.Optional("transport_train", default=True): bool,
                vol.Optional("transport_ferry", default=False): bool,
                vol.Optional("transport_school_bus", default=False): bool,
                vol.Optional(CONF_WALK_SPEED, default="normal"): vol.In(WALK_SPEEDS),
                vol.Optional(CONF_MAX_CONNECTIONS, default=""): str,
                vol.Optional(CONF_MAX_WALKING_DISTANCE, default=""): str,
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

