# EDJournal.py

## Purpose
Reads and parses Elite Dangerous journal files to track ship state, location, status, and game events. Provides real-time access to ship information through an auto-updating dictionary interface.

## Key Classes/Functions

### StationType (Enum)
- Represents different station types (Starport, Outpost, FleetCarrier, etc.)

### EDJournal
- Main class for journal file processing and ship state tracking

### Utility Functions
- `get_ship_size(ship)`: Returns ship size ('S', 'M', 'L') from journal ship name
- `get_ship_fullname(ship)`: Returns full display name of ship
- `check_fuel_scoop(modules)`: Detects if fuel scoop is equipped
- `check_adv_docking_computer(modules)`: Detects advanced docking computer
- `check_std_docking_computer(modules)`: Detects standard docking computer
- `check_sco_fsd(modules)`: Detects FSD with Supercruise Assist
- `check_station_type(station_type, station_name, station_services)`: Determines station type enum

### File I/O Functions
- `write_construction(data, filename)`: Saves construction depot data to JSON
- `read_construction(filename)`: Reads construction depot data from JSON

## Key Methods

- `__init__(cb)`: Initialize journal reader with callback function
- `ship_state()`: Returns current ship state dict, auto-updates from journal file
- `parse_line(log)`: Parses individual journal log entry and updates ship state
- `get_latest_log(path_logs)`: Finds most recently modified journal file
- `open_journal(log_name)`: Opens journal file for reading
- `get_file_modified_time()`: Returns journal file modification timestamp
- `reset_items()`: Clears transient state flags (attack, fighter destroyed)
- `process_construction_depot_details()`: Processes and logs construction depot data

## Dependencies

- json, os, datetime
- EDAP_data (ship maps)
- EDlogger
- WindowsKnownPaths

## Notes

- Leveraged EDAutopilot (https://github.com/skai2/EDAutopilot) as reference
- Dictionary lazy-loads: ship_state() checks for file changes before updating
- Maintains 40+ fields tracking ship location, fuel, cargo, modules, status
- Handles journal file rotation when game creates new journal
- Construction depot data saved to configs/construction.json
