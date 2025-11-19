"""API client for Transperth Journey Planner."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .const import JOURNEY_PLANNER_URL, TRANSPERTH_BASE_URL

_LOGGER = logging.getLogger(__name__)


@dataclass
class JourneyLeg:
    """Represents a single leg of a journey."""

    type: str  # walk, bus, train, ferry, cat
    description: str  # e.g., "Walk 501m", "Bus 276", "Train Airport Line"
    service_code: str | None  # e.g., "276", "AIR", "MAN", "Red"


@dataclass
class JourneyOption:
    """Represents a single journey option."""

    leave_time: str
    arrive_time: str
    travel_time: str  # e.g., "69 mins"
    legs: list[JourneyLeg]
    index: int


@dataclass
class JourneyData:
    """Represents journey data for a route."""

    options: list[JourneyOption]
    from_location: str
    to_location: str
    date: str
    time: str


class TransperthAPI:
    """API client for Transperth Journey Planner."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def get_journey_options(
        self,
        from_location: str,
        from_type: str,
        from_position: str,
        from_locality: str,
        to_location: str,
        to_type: str,
        to_position: str,
        to_locality: str,
        date: str,
        time: str,
        departure_option: str = "leave_after",
        transport_options: list[str] | None = None,
        walk_speed: str = "normal",
        max_connections: int | None = None,
        max_walking_distance: str | None = None,
    ) -> JourneyData:
        """Fetch journey options from Transperth Journey Planner.

        Args:
            from_location: Starting location
            from_type: Type of from location (e.g., "psma_addresses")
            from_position: Coordinates for from location (lat,lon)
            from_locality: Locality of from location
            to_location: Destination location
            to_type: Type of to location (e.g., "psma_addresses")
            to_position: Coordinates for to location (lat,lon)
            to_locality: Locality of to location
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            departure_option: "leave_after", "arrive_by", "earliest_trip", or "last_trip"
            transport_options: List of transport types to include
            walk_speed: "slow", "normal", or "fast"
            max_connections: Maximum number of connections
            max_walking_distance: Maximum walking distance (e.g., "300m", "600m")

        Returns:
            JourneyData object containing journey options
        """
        # Build query parameters - ensure all required fields are present
        params: dict[str, Any] = {}
        
        # Required parameters
        if from_location:
            params["from"] = from_location
        if from_type:
            params["fromtype"] = from_type
        if from_position:
            params["fromposition"] = from_position
        if from_locality:
            params["fromlocality"] = from_locality
        if to_location:
            params["to"] = to_location
        if to_type:
            params["totype"] = to_type
        if to_position:
            params["toposition"] = to_position
        if to_locality:
            params["tolocality"] = to_locality
        if date:
            params["date"] = date
        if time:
            params["time"] = time

        # Add departure option
        if departure_option == "leave_after":
            params["departureOption"] = "LeaveAfter"
        elif departure_option == "arrive_by":
            params["departureOption"] = "ArriveBy"
        elif departure_option == "earliest_trip":
            params["departureOption"] = "EarliestTrip"
        elif departure_option == "last_trip":
            params["departureOption"] = "LastTrip"
        else:
            # Default to LeaveAfter if not specified
            params["departureOption"] = "LeaveAfter"

        # Add transport options - at least one is required
        if transport_options and len(transport_options) > 0:
            if "bus" in transport_options:
                params["bus"] = "on"
            if "train" in transport_options:
                params["train"] = "on"
            if "ferry" in transport_options:
                params["ferry"] = "on"
            if "school_bus" in transport_options:
                params["schoolbus"] = "on"
        else:
            # Default to bus and train if none specified
            params["bus"] = "on"
            params["train"] = "on"

        # Add walk speed
        if walk_speed == "slow":
            params["walkSpeed"] = "Slow"
        elif walk_speed == "normal":
            params["walkSpeed"] = "Normal"
        elif walk_speed == "fast":
            params["walkSpeed"] = "Fast"

        # Add max connections
        if max_connections is not None:
            if max_connections == 0:
                params["maxConnections"] = "Direct"
            else:
                params["maxConnections"] = str(max_connections)

        # Add max walking distance
        if max_walking_distance:
            params["maxWalkingDistance"] = max_walking_distance

        # Validate required parameters
        required_params = ["from", "to", "fromposition", "toposition"]
        missing_params = [p for p in required_params if not params.get(p)]
        if missing_params:
            _LOGGER.error("Missing required parameters: %s", missing_params)
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Ensure at least one transport option is selected
        transport_params = ["bus", "train", "ferry", "schoolbus"]
        has_transport = any(params.get(p) == "on" for p in transport_params)
        if not has_transport:
            _LOGGER.warning("No transport options specified, defaulting to bus and train")
            params["bus"] = "on"
            params["train"] = "on"

        try:
            # First, visit the main journey planner page to establish a session
            # This might be required for the site to work properly
            try:
                _LOGGER.debug("Establishing session by visiting main page")
                self.session.get(
                    f"{TRANSPERTH_BASE_URL}/Journey-Planner",
                    timeout=10
                )
            except Exception as e:
                _LOGGER.debug("Could not visit main page (non-critical): %s", e)
            
            # Make request - ensure proper URL encoding
            _LOGGER.debug("Requesting journey options with params: %s", params)
            _LOGGER.debug("Full URL will be: %s?%s", JOURNEY_PLANNER_URL, "&".join([f"{k}={v}" for k, v in params.items()]))
            
            # Add Referer header to make request look more legitimate
            headers = {
                "Referer": f"{TRANSPERTH_BASE_URL}/Journey-Planner",
            }
            
            response = self.session.get(
                JOURNEY_PLANNER_URL,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            _LOGGER.debug("Response status: %s, URL: %s", response.status_code, response.url)
            _LOGGER.debug("Response headers: %s", dict(response.headers))

            # Parse HTML
            soup = BeautifulSoup(response.text, "lxml")
            
            # Check if we got redirected or got an error page
            page_title = soup.find("title")
            if page_title:
                title_text = page_title.get_text(strip=True)
                _LOGGER.debug("Page title: %s", title_text)
                if "error" in title_text.lower() or "not found" in title_text.lower():
                    _LOGGER.warning("Possible error page detected: %s", title_text)
            
            options = self._parse_journey_options(soup)
            
            if not options:
                _LOGGER.warning("No journey options found. Response length: %d bytes", len(response.text))
                # Check if the response contains the error messages we're seeing
                response_lower = response.text.lower()
                if "please specify where the journey starts" in response_lower:
                    _LOGGER.error("Page indicates 'from' parameter is missing. Check if parameters are being sent correctly.")
                    _LOGGER.debug("Actual request URL: %s", response.url)
                if "please specify where the journey ends" in response_lower:
                    _LOGGER.error("Page indicates 'to' parameter is missing. Check if parameters are being sent correctly.")
                if "please specify at least one transport option" in response_lower:
                    _LOGGER.error("Page indicates transport options are missing. Check if parameters are being sent correctly.")
                # Save a snippet of the HTML for debugging (first 2000 chars)
                _LOGGER.debug("HTML snippet: %s", response.text[:2000])
                # Also check if the parameters are actually in the URL
                _LOGGER.debug("Request URL contains 'from': %s", "from=" in response.url)
                _LOGGER.debug("Request URL contains 'to': %s", "to=" in response.url)

            return JourneyData(
                options=options,
                from_location=from_location,
                to_location=to_location,
                date=date,
                time=time,
            )

        except requests.RequestException as err:
            _LOGGER.error("Error fetching journey options: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Error parsing journey options: %s", err)
            raise

    def _parse_journey_options(self, soup: BeautifulSoup) -> list[JourneyOption]:
        """Parse journey options from HTML.

        Args:
            soup: BeautifulSoup object of the journey planner results page

        Returns:
            List of JourneyOption objects
        """
        options: list[JourneyOption] = []

        # Find the journey options table - try multiple selectors
        table = soup.find("table", id="jrne-opt-tbl")
        if not table:
            # Try alternative selector
            table = soup.find("table", class_="jrne-opt-tbl")
        if not table:
            # Try finding by caption text
            tables = soup.find_all("table")
            for tbl in tables:
                caption = tbl.find("caption")
                if caption and "Journey Options" in caption.get_text():
                    table = tbl
                    break
        
        if not table:
            _LOGGER.warning("Journey options table not found. Checking for error messages...")
            # Check for common error indicators
            error_divs = soup.find_all(["div", "p"], class_=re.compile(r"error|alert|warning", re.I))
            for err in error_divs:
                err_text = err.get_text(strip=True)
                if err_text:
                    _LOGGER.warning("Possible error message: %s", err_text)
            return options

        # Find all table rows (skip header)
        rows = table.find("tbody")
        if not rows:
            _LOGGER.warning("Journey options tbody not found")
            return options

        journey_rows = rows.find_all("tr", recursive=False)
        if not journey_rows:
            _LOGGER.warning("No journey option rows found")
            return options

        for idx, row in enumerate(journey_rows, start=1):
            try:
                # Extract leave time
                leave_cell = row.find("td", class_="itemLeave")
                leave_time = ""
                if leave_cell:
                    leave_text = leave_cell.get_text(strip=True)
                    # Try to find time pattern
                    time_match = re.search(r"(\d{1,2}:\d{2}(?:am|pm))", leave_text)
                    if time_match:
                        leave_time = time_match.group(1)
                    else:
                        # Fallback: just use the text
                        leave_time = leave_text.strip()

                # Extract arrive time
                arrive_cell = row.find("td", class_="itemArrive")
                arrive_time = arrive_cell.get_text(strip=True) if arrive_cell else ""

                # Extract travel time
                time_cell = row.find("td", class_="itemTime")
                travel_time = time_cell.get_text(strip=True) if time_cell else ""

                # Extract route legs
                route_cell = row.find("td", class_="itemRoute")
                legs: list[JourneyLeg] = []
                if route_cell:
                    leg_list = route_cell.find("ol")
                    if leg_list:
                        leg_items = leg_list.find_all("li", recursive=False)
                        for leg_item in leg_items:
                            leg_type = "walk"  # default
                            description = ""
                            service_code = None

                            # Check icon class to determine type
                            icon = leg_item.find("i")
                            if icon:
                                icon_class = icon.get("class", [])
                                if isinstance(icon_class, list):
                                    icon_class = " ".join(icon_class)
                                
                                if "icon-walk" in icon_class:
                                    leg_type = "walk"
                                elif "icon-bus-circ" in icon_class:
                                    leg_type = "bus"
                                elif "icon-train-circ" in icon_class:
                                    leg_type = "train"
                                elif "icon-ferry" in icon_class:
                                    leg_type = "ferry"
                                elif "icon-cat" in icon_class:
                                    leg_type = "cat"

                            # Extract description
                            span = leg_item.find("span")
                            if span:
                                description = span.get_text(strip=True)

                            # Extract service code
                            service_code_div = leg_item.find("div", class_="tp-service-code")
                            if service_code_div:
                                service_code = service_code_div.get_text(strip=True)

                            legs.append(
                                JourneyLeg(
                                    type=leg_type,
                                    description=description,
                                    service_code=service_code,
                                )
                            )

                options.append(
                    JourneyOption(
                        leave_time=leave_time,
                        arrive_time=arrive_time,
                        travel_time=travel_time,
                        legs=legs,
                        index=idx,
                    )
                )

            except Exception as err:
                _LOGGER.warning("Error parsing journey option %d: %s", idx, err)
                continue

        return options

