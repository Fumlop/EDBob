# EDAP_data.py

## Purpose
Static data definitions for Elite Dangerous including game status flags, ship specifications, commodities, and performance metrics.

## Key Classes/Functions

### Status.json Flag Constants
- **Flags**: 32-bit integer containing game state (Docked, Landed, Shields, Supercruise, FSD states, etc.)
- **Flags2**: Additional flags for Odyssey features (OnFoot, InTaxi, Glide Mode, cold/heat conditions, etc.)
- **GuiFocus**: Constants for HUD focus areas (Galaxy Map, System Map, FSS, SAA, Codex, etc.)

### Data Maps

#### Ship Maps
- `ship_name_map`: Maps journal ship ID to display name (48 ships: Anaconda, Python, etc.)
- `ship_size_map`: Maps ship ID to size class ('S', 'M', 'L')
- `ship_rpy_sc_50`: Roll/Pitch/Yaw rates at 50% supercruise throttle (deg/sec)
- `ship_rpy_sc_100`: Roll/Pitch/Yaw rates at 100% supercruise throttle (deg/sec)

#### Commodity Data
- `commodities`: Dictionary of 14 categories with 300+ commodity items
  - Categories: Chemicals, Consumer Items, Foods, Industrial Materials, Machinery, Medicines, Metals, Minerals, Salvage, Slavery, Technology, Textiles, Waste, Weapons, Legal Drugs

### Functions
- `sorted_commodities()`: Returns alphabetically sorted list of all commodities

## Dependencies

None (static data only)

## Notes

- Flag constants based on Elite Dangerous Status.json format
- Ship data sourced from: https://forums.frontier.co.uk/threads/supercruise-handling-of-ships.396845/
- Commodity data from EDMarketConnector (https://github.com/EDCD/EDMarketConnector)
- All ship handling metrics normalized to degrees per second
- Timestamp adjustments account for in-game year offset (1286 years in future)
