# Transperth Journey Planner for Home Assistant

A Home Assistant integration that provides sensors for Transperth public transport journey options. This integration allows you to monitor multiple routes with different departure times, dates, and route configurations.

## Features

- **Multiple Route Support**: Configure multiple journey routes, each with its own sensors
- **Flexible Configuration**: Set departure/arrival times, dates, transport options, and more
- **Multiple Journey Options**: Each route provides up to 5 journey option sensors
- **Detailed Attributes**: Each sensor includes:
  - Leave and arrival times
  - Travel time
  - Route legs (walking, bus, train, ferry, CAT)
  - Service codes for each leg
  - Full route information

## Installation

### Option 1: HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install "Transperth Journey Planner"
3. Restart Home Assistant
4. Add the integration via Configuration > Integrations

### Option 2: Manual Installation

1. Download the latest release
2. Copy the `transperth_journey_planner` folder to your `custom_components` directory
3. Restart Home Assistant
4. Add the integration via Configuration > Integrations

## Configuration

1. Go to **Configuration** > **Integrations**
2. Click **Add Integration** and search for "Transperth Journey Planner"
3. Add your first route:
   - **Route Name**: A friendly name for this route (e.g., "Home to Work")
   - **From**: Starting location address
   - **From Type**: Type of location (default: "psma_addresses")
   - **From Position**: Coordinates in format "lat,lon" (e.g., "-31.963218,116.05422")
   - **From Locality**: Locality/suburb name
   - **To**: Destination address
   - **To Type**: Type of location (default: "psma_addresses")
   - **To Position**: Coordinates in format "lat,lon"
   - **To Locality**: Locality/suburb name
   - **Date**: Date in YYYY-MM-DD format (optional, defaults to today)
   - **Time**: Time in HH:MM format (optional, defaults to current time)
   - **Departure Option**: "leave_after", "arrive_by", "earliest_trip", or "last_trip"
   - **Transport Options**: Select which transport types to include (bus, train, ferry, school_bus)
   - **Walk Speed**: "slow", "normal", or "fast"
   - **Max Connections**: Maximum number of connections (optional)
   - **Max Walking Distance**: Maximum walking distance (e.g., "300m", "600m")
4. Add additional routes if desired
5. Complete the setup

## Sensors

For each configured route, the integration creates up to 5 sensors (one for each journey option):

- **sensor.transperth_[route_name]_option_1**: First journey option
- **sensor.transperth_[route_name]_option_2**: Second journey option
- **sensor.transperth_[route_name]_option_3**: Third journey option
- **sensor.transperth_[route_name]_option_4**: Fourth journey option
- **sensor.transperth_[route_name]_option_5**: Fifth journey option

### Sensor State

The sensor state shows the journey time range: `"08:05am → 09:14am"`

### Sensor Attributes

Each sensor includes the following attributes:

- `route_name`: Name of the route
- `option_index`: Index of this option (1-5)
- `leave_time`: Departure time
- `arrive_time`: Arrival time
- `travel_time`: Total travel time (e.g., "69 mins")
- `from_location`: Starting location
- `to_location`: Destination location
- `date`: Journey date
- `time`: Journey time
- `legs`: List of journey legs with:
  - `type`: Type of leg (walk, bus, train, ferry, cat)
  - `description`: Description (e.g., "Walk 501m", "Bus 276", "Train Airport Line")
  - `service_code`: Service code (e.g., "276", "AIR", "MAN", "Red")
- `leg_count`: Number of legs in the journey

## Example Usage

### Getting the Next Departure Time

```yaml
template:
  - sensor:
      - name: "Next Bus to Work"
        state: >
          {{ state_attr('sensor.transperth_home_to_work_option_1', 'leave_time') }}
```

### Checking if a Route is Available

```yaml
template:
  - binary_sensor:
      - name: "Route Available"
        state: >
          {{ states('sensor.transperth_home_to_work_option_1') != 'unavailable' }}
```

### Displaying Route Details

```yaml
template:
  - sensor:
      - name: "Journey Details"
        state: >
          {{ state_attr('sensor.transperth_home_to_work_option_1', 'travel_time') }}
        attributes:
          route: >
            {{ state_attr('sensor.transperth_home_to_work_option_1', 'legs') | map(attribute='description') | join(' → ') }}
```

## Options

You can configure the scan interval in the integration options:

- **Scan Interval**: How often to update journey data (minimum: 60 seconds, default: 300 seconds)

## Finding Coordinates

To find the coordinates for your locations:

1. Visit [Google Maps](https://www.google.com/maps)
2. Search for your location
3. Right-click on the location and select the coordinates
4. Copy the latitude and longitude (e.g., "-31.963218,116.05422")

Alternatively, you can use the Transperth Journey Planner website to find the exact format needed.

## Troubleshooting

### No Journey Options Found

- Verify your coordinates are correct
- Check that the date and time are valid
- Ensure transport options are selected
- Check the Home Assistant logs for errors

### Sensors Show as Unavailable

- Check your internet connection
- Verify the Transperth website is accessible
- Check the Home Assistant logs for API errors
- Try increasing the scan interval

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.transperth_journey_planner: debug
```

## Limitations

- The integration scrapes the Transperth website, so it may break if the website structure changes
- Journey data is updated based on the scan interval (default: 5 minutes)
- Maximum of 5 journey options per route
- Requires internet connection to fetch journey data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Transperth for providing the Journey Planner service
- Home Assistant community for the integration framework

