# FleetCarrierMonitorDataParser.py

## Purpose
Parses FleetCarrier.json file from ED Market Connector's Fleet Carrier Monitor plugin. Extracts and consolidates fleet carrier cargo inventory with commodity tracking.

## Key Classes/Functions
- FleetCarrierRawCargo: Dataclass representing raw cargo entry with mission/origin metadata
- FleetCarrierCargo: TypedDict for simplified cargo (commodity, locName, qty)
- FleetCarrierMonitorDataParser: Reads fleet carrier data from JSON file

## Key Methods
- get_fleetcarrier_data(): Loads fleet carrier data from JSON, caches if file unchanged, returns None if file doesn't exist
- get_current_cargo_list(): Returns list of raw cargo with metadata (may have duplicates for same commodity)
- get_consolidated_cargo_dict(): Returns alphabetically sorted dict consolidating duplicate items by summing quantities

## Data Classes
- FleetCarrierRawCargo: commodity, locName, mission (bool), originSystem (int), qty, stolen (bool), value
- FleetCarrierCargo: commodity, locName, qty (simplified)

## Dependencies
- os: File operations
- json: JSON parsing
- dataclasses: Data class definitions
- EDlogger: Logging

## Notes
- File path must be provided in constructor or passed as attribute
- Returns None gracefully if file doesn't exist
- Handles duplicates by consolidating quantities for same commodity
- Includes mission flag, origin system, and stolen status in raw data
- Consolidation alphabetizes by localized name for UI consistency
- Based on FDevIDs Fleet Carrier API specification
