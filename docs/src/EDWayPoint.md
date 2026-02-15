# EDWayPoint.py

## Purpose
Loads and processes waypoint routes from JSON files, automating multi-stop trading missions including jumps, supercruise, docking, and commodity trading. Tracks completion status and trading statistics.

## Key Classes/Functions
- **EDWayPoint**: Main class managing waypoint navigation and trading

## Key Methods
- **load_waypoint_file()**: Loads waypoints from JSON file with validation
- **get_waypoint()**: Returns next uncompleted waypoint, handles REPEAT entries
- **mark_waypoint_complete()**: Marks waypoint as done and persists to file
- **mark_all_waypoints_not_complete()**: Resets all waypoints to incomplete (for REPEAT)
- **waypoint_assist()**: Main orchestration loop for multi-stop route execution
- **execute_trade()**: Handles buying/selling at stations, fleet carriers, and construction ships
- **log_stats()**: Applies time penalties for colonisation/construction ship trades

## Waypoint JSON Structure
Each waypoint requires:
- SystemName, StationName
- GalaxyBookmarkType, GalaxyBookmarkNumber (galaxy map bookmarks)
- SystemBookmarkType, SystemBookmarkNumber (system map bookmarks)
- SellCommodities, BuyCommodities (dictionaries with quantities)
- FleetCarrierTransfer, UpdateCommodityCount, Skip, Completed flags

GlobalShoppingList special entry handles additional buy requirements across all stations.

## Key Attributes
- **waypoints**: Dictionary of loaded waypoint entries
- **step**: Current waypoint index
- **stats_log**: Counters for station types visited (Colonisation, Construction, Fleet Carrier, Station)

## Dependencies
- CargoParser: Reads player cargo manifest from journal
- MarketParser: Reads station commodity market data
- StatusParser: Reads game status from journal
- EDKeys: Sends keyboard input
- EDAP_data: Station type and flag constants
- EDJournal: StationType enum

## Notes
- Validates waypoint JSON structure on load (required fields checking)
- Handles station type variations (orbital, outpost, fleet carrier, construction ship)
- Applies exponential time penalties for construction/colonisation trades
- Supports 'ALL' as commodity key for bulk operations
- Updates waypoint files with completion status and remaining quantities
- Continues jumping/trading until complete or error
