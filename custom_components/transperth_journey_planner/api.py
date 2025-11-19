"""API client for Transperth Journey Planner."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .const import JOURNEY_PLANNER_API_URL, JOURNEY_PLANNER_URL, TRANSPERTH_BASE_URL

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
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-GB,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self._request_verification_token: str | None = None
        self._module_id: str | None = None
        self._tab_id: str | None = None

    def _get_session_tokens(self) -> None:
        """Get RequestVerificationToken and other session tokens from the Journey Planner page."""
        try:
            # Visit the Journey Planner page to get cookies and tokens
            response = self.session.get(
                f"{TRANSPERTH_BASE_URL}/Journey-Planner",
                timeout=10
            )
            response.raise_for_status()
            
            # Parse HTML to find RequestVerificationToken
            soup = BeautifulSoup(response.text, "lxml")
            
            # Find the RequestVerificationToken input
            token_input = soup.find("input", {"name": "__RequestVerificationToken"})
            if token_input:
                self._request_verification_token = token_input.get("value")
                _LOGGER.debug("Found RequestVerificationToken")
            
            # Try to find ModuleId and TabId from script tags or data attributes
            # These might be in JavaScript variables or data attributes
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    # Look for ModuleId
                    module_match = re.search(r'ModuleId["\']?\s*[:=]\s*["\']?(\d+)', script.string)
                    if module_match:
                        self._module_id = module_match.group(1)
                        _LOGGER.debug("Found ModuleId: %s", self._module_id)
                    
                    # Look for TabId
                    tab_match = re.search(r'TabId["\']?\s*[:=]\s*["\']?(\d+)', script.string)
                    if tab_match:
                        self._tab_id = tab_match.group(1)
                        _LOGGER.debug("Found TabId: %s", self._tab_id)
            
            # Default values if not found
            if not self._module_id:
                self._module_id = "5325"  # Default from curl example
            if not self._tab_id:
                self._tab_id = "140"  # Default from curl example
                
        except Exception as e:
            _LOGGER.warning("Could not get session tokens: %s", e)
            # Use defaults
            self._request_verification_token = None
            self._module_id = "5325"
            self._tab_id = "140"

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
        """Fetch journey options from Transperth Journey Planner using JSON API.

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
            max_connections: Maximum number of connections (-1 for unlimited)
            max_walking_distance: Maximum walking distance in meters (e.g., "2000")

        Returns:
            JourneyData object containing journey options
        """
        # Validate required parameters
        if not from_location or not from_location.strip():
            raise ValueError("from_location is required")
        if not to_location or not to_location.strip():
            raise ValueError("to_location is required")
        if not from_position or not from_position.strip():
            raise ValueError("from_position is required")
        if not to_position or not to_position.strip():
            raise ValueError("to_position is required")
        
        # Get session tokens
        self._get_session_tokens()
        
        # Build JSON payload
        payload: dict[str, Any] = {
            "FromLocationName": from_location.strip(),
            "FromLocationType": from_type.strip() if from_type else "psma_addresses",
            "FromLocationPosition": from_position.strip(),
            "ToLocationName": to_location.strip(),
            "ToLocationType": to_type.strip() if to_type else "psma_addresses",
            "ToLocationPosition": to_position.strip(),
            "JourneyDate": date.strip() if date else "",
            "JourneyTime": time.strip() if time else "",
        }
        
        # Add optional fields
        if from_locality and from_locality.strip():
            payload["FromLocationLocality"] = from_locality.strip()
        if to_locality and to_locality.strip():
            payload["ToLocationLocality"] = to_locality.strip()
        
        # Transport options
        payload["TransportBus"] = "bus" in (transport_options or [])
        payload["TransportTrain"] = "train" in (transport_options or [])
        payload["TransportFerry"] = "ferry" in (transport_options or [])
        payload["TransportSchoolBus"] = "school_bus" in (transport_options or [])
        
        # Default to bus and train if none specified
        if not any([payload["TransportBus"], payload["TransportTrain"], payload["TransportFerry"], payload["TransportSchoolBus"]]):
            payload["TransportBus"] = True
            payload["TransportTrain"] = True
        
        # Walk speed
        walk_speed_map = {"slow": "SLOW", "normal": "NORMAL", "fast": "FAST"}
        payload["WalkSpeed"] = walk_speed_map.get(walk_speed, "NORMAL")
        
        # Max connections (-1 for unlimited, or specific number)
        if max_connections is not None:
            payload["MaxConnections"] = str(max_connections)
        else:
            payload["MaxConnections"] = "-1"
        
        # Max walking distance (default 2000m from example)
        if max_walking_distance:
            # Remove 'm' suffix if present
            distance = max_walking_distance.replace("m", "").replace("M", "").strip()
            payload["MaxWalkingDistance"] = distance
        else:
            payload["MaxWalkingDistance"] = "2000"
        
        # Additional fields from example
        payload["ReturnNotes"] = True
        payload["ReturnNoteCodes"] = "DV,LM,CM,JC,TC,BG,FG,LK"
        payload["MaxJourneys"] = "5"
        
        try:
            # Build headers
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "Referer": f"{TRANSPERTH_BASE_URL}/Journey-Planner",
                "Origin": TRANSPERTH_BASE_URL,
            }
            
            if self._request_verification_token:
                headers["RequestVerificationToken"] = self._request_verification_token
            
            if self._module_id:
                headers["ModuleId"] = self._module_id
            
            if self._tab_id:
                headers["TabId"] = self._tab_id
            
            _LOGGER.debug("Making POST request to JSON API with payload: %s", json.dumps(payload, indent=2))
            
            # Make POST request
            response = self.session.post(
                JOURNEY_PLANNER_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if data.get("result") != "success":
                _LOGGER.error("API returned error: %s", data)
                raise ValueError(f"API error: {data.get('result', 'unknown')}")
            
            # Parse journey options from JSON
            options = self._parse_json_journey_options(data.get("data", []))
            
            _LOGGER.debug("Found %d journey options", len(options))
            
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
        except json.JSONDecodeError as err:
            _LOGGER.error("Error parsing JSON response: %s", err)
            _LOGGER.debug("Response text: %s", response.text[:1000])
            raise
        except Exception as err:
            _LOGGER.error("Error processing journey options: %s", err)
            raise

    def _parse_json_journey_options(self, journeys: list[dict[str, Any]]) -> list[JourneyOption]:
        """Parse journey options from JSON API response.

        Args:
            journeys: List of journey dictionaries from the API response

        Returns:
            List of JourneyOption objects
        """
        options: list[JourneyOption] = []

        for journey in journeys:
            try:
                # Extract basic journey info
                leave_time = journey.get("JnyDisplayDepartTime", "")
                arrive_time = journey.get("JnyDisplayArriveTime", "")
                travel_time = journey.get("JnyDuration", "")
                journey_number = journey.get("JnyNumber", 0)

                # Parse trip details into legs
                legs: list[JourneyLeg] = []
                trip_details = journey.get("JnyTripDetails", [])
                
                for trip in trip_details:
                    trip_vehicle = trip.get("TripVehicle", "").lower()
                    route_code = trip.get("RouteCode")
                    display_title = trip.get("DisplayTripTitle", "")
                    display_duration = trip.get("DisplayTripDuration", "")
                    
                    # Determine leg type
                    if trip_vehicle == "walk" or "walk" in display_title.lower():
                        leg_type = "walk"
                    elif trip_vehicle == "bus" or "bus" in display_title.lower():
                        leg_type = "bus"
                    elif trip_vehicle == "train" or "train" in display_title.lower():
                        leg_type = "train"
                    elif trip_vehicle == "ferry" or "ferry" in display_title.lower():
                        leg_type = "ferry"
                    elif "cat" in display_title.lower():
                        leg_type = "cat"
                    else:
                        leg_type = "walk"  # default
                    
                    # Build description
                    description_parts = []
                    if route_code:
                        description_parts.append(route_code)
                    if display_title:
                        # Clean up the title
                        title = display_title.replace("Catch ", "").replace("Walk to ", "").replace("Walk ", "")
                        description_parts.append(title)
                    if display_duration:
                        description_parts.append(f"({display_duration})")
                    
                    description = " ".join(description_parts) if description_parts else display_title or trip_vehicle
                    
                    legs.append(
                        JourneyLeg(
                            type=leg_type,
                            description=description,
                            service_code=route_code,
                        )
                    )

                options.append(
                    JourneyOption(
                        leave_time=leave_time,
                        arrive_time=arrive_time,
                        travel_time=travel_time,
                        legs=legs,
                        index=journey_number,
                    )
                )

            except Exception as err:
                _LOGGER.warning("Error parsing journey option: %s", err)
                continue

        return options

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

