# EDWayPoint.py -- Waypoint Route & Trade Engine

## Purpose

Loads waypoint routes from JSON files and orchestrates multi-stop trading missions: galaxy map bookmark navigation, system jumps, supercruise, docking, and commodity buy/sell/transfer at stations, fleet carriers, and colonisation/construction ships. Tracks completion status per waypoint and persists progress back to disk.

Lives in `src/autopilot/EDWayPoint.py`. Instantiated by `EDAutopilot`.

## Class: EDWayPoint

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `is_odyssey` | bool | (unused, kept for signature compatibility) |

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Reference to parent autopilot |
| `filename` | str | Path to the currently loaded waypoint JSON file |
| `waypoints` | dict | Loaded waypoint entries keyed by step label |
| `num_waypoints` | int | Total number of waypoint entries |
| `step` | int | Current waypoint index (0-based) |
| `stats_log` | dict | Counters per station type: Colonisation, Construction, Fleet Carrier, Station |
| `market_parser` | MarketParser | Reads station commodity market data from journal |
| `cargo_parser` | CargoParser | Reads player cargo manifest from journal |
| `_last_bookmark_set` | tuple or None | Last (bookmark_type, bookmark_num) set in galaxy map, avoids redundant sets |

## Properties

| Property | Returns | Description |
|---|---|---|
| `_waypoint_path` | str | Resolved path to the current waypoint file (`./waypoints/<filename>`) |

## Methods

### File I/O

| Method | Returns | Description |
|---|---|---|
| `load_waypoint_file(filename)` | bool | Load and validate a waypoint JSON file. Sets `self.waypoints`, `self.num_waypoints`, `self.filename`. Returns False if file missing or invalid. |
| `_read_waypoints(filename)` | dict or None | Read JSON, validate `GlobalShoppingList` exists, validate required fields per entry type. Returns None on any validation failure. |
| `write_waypoints(data, filename)` | None | Write waypoint dict to JSON file. If `data` is None, writes `self.waypoints`. |

### Waypoint Iteration

| Method | Returns | Description |
|---|---|---|
| `get_waypoint()` | tuple[str, dict] or (None, None) | Returns the next uncompleted, non-skipped waypoint key and entry. Handles `REPEAT` entries by resetting all waypoints to incomplete. Skips `GlobalShoppingList` and entries with `Skip=True` or `Completed=True`. |
| `mark_waypoint_complete(key)` | None | Sets `Completed=True` on the given waypoint and persists to file. |
| `mark_all_waypoints_not_complete()` | None | Resets all waypoints to `Completed=False`, resets `self.step` to 0, writes to file, calls `log_stats()`. |

### Trade Execution

| Method | Returns | Description |
|---|---|---|
| `execute_trade(ap, dest_key)` | int or None | Main trade dispatcher. Routes to colonisation/construction sell, fleet carrier transfer, or regular station buy/sell based on `exp_station_type`. Returns total units bought, 0 if nothing traded, or None for delivery-only (colonisation/construction). |
| `_buy_one(ap, name, qty, cargo_capacity)` | tuple[int, bool] | Buy a single commodity. Returns (units_bought, cargo_full). Waits for status file update after purchase. |
| `sell_to_colonisation_ship(ap)` | None | Delegates to `stn_svcs_in_ship.sell_to_colonisation_ship()`. |

### Construction Depot Sync

| Method | Returns | Description |
|---|---|---|
| `_sync_from_construction_depot()` | None | Reads `ColonisationConstructionDepot` journal event, computes remaining needs, updates `GlobalShoppingList` and per-waypoint `BuyCommodities` counts to match depot state. Writes changes to file. |

### Statistics

| Method | Returns | Description |
|---|---|---|
| `log_stats()` | None | Applies exponential time penalty: sleeps for `max(1.5^colonisation_count, 1.5^construction_count)` seconds. |
| `reset_stats()` | None | Zeros all `stats_log` counters. |

### Main Orchestration

| Method | Returns | Description |
|---|---|---|
| `waypoint_assist(keys, scr_reg)` | None | Main waypoint loop. Loads waypoints, auto-detects starting waypoint if docked, syncs construction depot, then loops: trade at current station, set galaxy bookmark, undock, jump to next system, supercruise to station, dock. Stops on completion, abort, construction complete, or buy failure. |

## Waypoint JSON Structure

### Required Special Entry

- **`GlobalShoppingList`** -- must exist in every waypoint file. Contains shared buy commodities applied at all regular stations.

### GlobalShoppingList Fields

| Field | Type | Description |
|---|---|---|
| `BuyCommodities` | dict | Commodity name to quantity mapping, bought at every station |
| `UpdateCommodityCount` | bool | If True, decrement quantities after purchase |
| `Skip` | bool | If True, ignore global shopping list |

### Per-Waypoint Fields

| Field | Type | Description |
|---|---|---|
| `SystemName` | str | Target star system. Set to `"REPEAT"` to loop back to first waypoint. |
| `StationName` | str | Target station/carrier name |
| `GalaxyBookmarkType` | str | Galaxy map bookmark category |
| `GalaxyBookmarkNumber` | int | Galaxy map bookmark index (must be > 0) |
| `SystemBookmarkType` | str | System map bookmark category |
| `SystemBookmarkNumber` | int | System map bookmark index |
| `SellCommodities` | dict | Commodity name to quantity. Use key `"ALL"` to sell everything. |
| `BuyCommodities` | dict | Commodity name to quantity. Use key `"ALL"` to buy anything available. |
| `UpdateCommodityCount` | bool | If True, decrement buy/sell quantities after trade |
| `FleetCarrierTransfer` | bool | If True, use fleet carrier transfer mode instead of market buy/sell |
| `Skip` | bool | If True, skip this waypoint entirely |
| `Completed` | bool | Set to True when waypoint is done; reset on REPEAT |

## Key Workflows

### Waypoint Assist (full trade route)

```
waypoint_assist(keys, scr_reg):
  1. Reset all waypoints to incomplete
  2. Auto-detect: if docked at a known waypoint station, start there
  3. Sync commodity counts from construction depot journal data
  4. Loop:
     a. Get next uncompleted waypoint
     b. If docked:
        - Check construction complete (stop if so)
        - execute_trade() at current station
        - Check buy result (stop if nothing available or all fulfilled)
        - Mark waypoint complete
        - Get NEXT waypoint for navigation target
        - Set galaxy map bookmark
        - Undock (waypoint_undock_seq)
     c. Navigation:
        - Set galaxy map bookmark (if not already set)
        - If different system: sc_engage, SCO boost, jump via do_route_jump
        - If same system: supercruise_to_station (blocks until docked)
        - If no target: reset all waypoints
  5. On completion: log total distance jumped
```

### Execute Trade (station dispatch)

```
execute_trade(ap, dest_key):
  Check station type:
  - ColonisationShip / SpaceConstructionDepot:
      goto_construction_services -> sell_to_colonisation_ship
      Return None (delivery only)
  - FleetCarrier with FleetCarrierTransfer:
      transfer_to_fleetcarrier (sell) / transfer_from_fleetcarrier (buy)
  - Regular Station / Fleet Carrier (market mode):
      1. goto_commodities_market, wait for market data refresh
      2. SELL: iterate sell_commodities, handle "ALL" key, update counts
      3. BUY: sorted by quantity (lowest first to fit all)
         - Per-waypoint buy_commodities
         - GlobalShoppingList buy_commodities
         - Stop if cargo full
      4. Write updated waypoints, return to cockpit view
```

## Dependencies

| Module | Purpose |
|---|---|
| `CargoParser` | Read player cargo manifest from journal files |
| `MarketParser` | Read station commodity market data from journal files |
| `EDKeys` | Send keyboard input to Elite Dangerous |
| `EDJournal` | `StationType` enum for station classification |
| `EDAP_data` | `FlagsDocked`, `FlagsLanded` status flag constants |
| `MousePoint` | Mouse interaction (imported but used via ap subsystems) |
| `EDAutopilot` | Parent autopilot -- provides `galaxy_map`, `stn_svcs_in_ship`, `internal_panel`, `ship_control`, `nav_route`, `status`, `jn` |

## Notes

- ~640 lines, single class focused on waypoint orchestration and trade logic
- Validates waypoint JSON on load with per-field checking; rejects files missing `GlobalShoppingList`
- Handles REPEAT entries for continuous loop routes (e.g., hauling runs)
- Auto-detects starting waypoint when already docked at a known station (including partial name match for colonisation/construction ships)
- Syncs commodity counts from `ColonisationConstructionDepot` journal events to keep waypoint quantities accurate
- Exponential sleep penalty in `log_stats()` scales with colonisation/construction visit count
- Supports `"ALL"` as commodity key for bulk sell (all cargo) and bulk buy (all buyable market items)
- Buy order is sorted ascending by quantity to maximize variety of goods loaded
- Stops automatically when construction is detected as complete, or when buy lists are fulfilled (counts at 0)
