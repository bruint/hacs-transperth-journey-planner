"""Constants for the Transperth Journey Planner integration."""

DOMAIN = "transperth_journey_planner"

DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
MIN_SCAN_INTERVAL = 60  # 1 minute

CONF_FROM = "from"
CONF_FROM_TYPE = "fromtype"
CONF_FROM_POSITION = "fromposition"
CONF_FROM_LOCALITY = "fromlocality"
CONF_TO = "to"
CONF_TO_TYPE = "totype"
CONF_TO_POSITION = "toposition"
CONF_TO_LOCALITY = "tolocality"
CONF_DATE = "date"
CONF_TIME = "time"
CONF_DEPARTURE_OPTION = "departure_option"
CONF_TRANSPORT_OPTIONS = "transport_options"
CONF_WALK_SPEED = "walk_speed"
CONF_MAX_CONNECTIONS = "max_connections"
CONF_MAX_WALKING_DISTANCE = "max_walking_distance"

TRANSPERTH_BASE_URL = "https://www.transperth.wa.gov.au"
JOURNEY_PLANNER_URL = f"{TRANSPERTH_BASE_URL}/Journey-Planner/Results"
JOURNEY_PLANNER_API_URL = f"{TRANSPERTH_BASE_URL}/API/SilverRailRestService/SilverRailService/PlanJourney"

DEPARTURE_OPTIONS = ["leave_after", "arrive_by", "earliest_trip", "last_trip"]
WALK_SPEEDS = ["slow", "normal", "fast"]
TRANSPORT_OPTIONS = ["bus", "train", "ferry", "school_bus"]

