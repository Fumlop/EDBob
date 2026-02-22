# EDJournal.py -- Journal File Processor

## Purpose

Reads and parses Elite Dangerous journal files to track ship state in real time.
Opens the latest `Journal.*.log` file from the Saved Games directory, tails it for new
entries, and maintains a dictionary of ship state fields. Callers access the state via
`ship_state()`, which transparently re-reads the file when it has been modified.
Lives in `src/ed/EDJournal.py`. Originally based on EDAutopilot (https://github.com/skai2/EDAutopilot).

## Architecture

- `EDJournal` class opens the journal once and tails it on each `ship_state()` call
- File rotation handled: detects when a new journal file appears and re-opens
- Partial/split line buffering for mid-write robustness
- Callback system (`ap_ckb`) for GUI logging
- Construction depot data persisted to `configs/construction.json`

## Enums

| Enum | Values | Description |
|---|---|---|
| `StationType` | Unknown=0, Starport=1, Outpost=2, FleetCarrier=3, SquadronCarrier=4, ColonisationShip=5, SpaceConstructionDepot=6, PlanetaryConstructionDepot=7, SurfaceStation=8 | Classifies docked/target station type |

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `get_ship_size(ship)` | `str` | Ship size ('S', 'M', 'L') from journal ship name (e.g. 'diamondbackxl'). Returns '' if unknown. Uses `ship_size_map` from EDAP_data. |
| `get_ship_fullname(ship)` | `str` | Full display name (e.g. 'Diamondback Explorer') from journal ship name. Returns '' if unknown. Uses `ship_name_map` from EDAP_data. |
| `_has_module(modules, item_search, slot)` | `bool` | Check if ship modules list contains a module whose Item field matches `item_search` (case-insensitive). If `slot` given, only checks that slot. Returns True if `modules` is None (assumes fitted when data unavailable). |
| `check_fuel_scoop(modules)` | `bool` | Detects if fuel scoop is equipped. Delegates to `_has_module` with "fuelscoop". |
| `check_adv_docking_computer(modules)` | `bool` | Detects advanced docking computer. Delegates to `_has_module` with "dockingcomputer_advanced". |
| `check_std_docking_computer(modules)` | `bool` | Detects standard docking computer. Delegates to `_has_module` with "dockingcomputer_standard". |
| `check_sco_fsd(modules)` | `bool` | Detects SCO FSD (overcharge). Delegates to `_has_module` with "overcharge" in FrameShiftDrive slot. |
| `check_station_type(station_type, station_name, station_services)` | `StationType` | Determines station type enum from journal fields. Handles special cases: SurfaceStation with "colonisationship" in name returns ColonisationShip; FleetCarrier with "squadronbank" service returns SquadronCarrier. Falls back to `_STATION_TYPE_MAP` lookup. |
| `write_construction(data, filename)` | `bool` | Save construction depot dict to JSON file (default `./configs/construction.json`). Returns True on success. |
| `read_construction(filename)` | `dict` or `None` | Read construction depot dict from JSON file. Returns None on error. |
| `dummy_cb(msg, body)` | `None` | No-op callback for testing. |
| `main()` | `None` | Test harness: creates EDJournal, polls `ship_state()` every 5s. |

## Module-Level Constants

| Constant | Type | Description |
|---|---|---|
| `_STATION_TYPE_MAP` | `dict` | Maps lowercase station type strings to `StationType` enum values. Covers coriolis, orbis, ocellus, bernal, dodec, asteroidbase, outpost, crateroutpost, spaceconstructiondepot, planetaryconstructiondepot. |

## EDJournal Class

### Ship State Dictionary

The `self.ship` dict contains the following fields, updated by `parse_line()`:

| Field | Type | Description |
|---|---|---|
| `time` | `int` | Seconds since journal file was last modified at init |
| `odyssey` | `bool` | Always True (hardset for ED 4.0) |
| `status` | `str` | Current status: 'in_space', 'in_supercruise', 'in_station', 'starting_hyperspace', 'starting_supercruise', 'starting_docking', 'dockinggranted', 'dockingdenied' |
| `type` | `str` or None | Ship type (lowercase, e.g. 'diamondbackxl') |
| `location` | `str` or None | Current star system name |
| `star_class` | `str` or None | Star class of current/target star (e.g. 'K', 'M') |
| `target` | `str` or None | FSD target system name, None if at destination |
| `fighter_destroyed` | `bool` | True if fighter was destroyed (transient, reset after read) |
| `shieldsup` | `bool` | True if shields are up |
| `under_attack` | `bool` | True if under attack (transient, reset after read) |
| `interdicted` | `bool` | True if interdicted |
| `no_dock_reason` | `str` or None | Reason string if docking denied |
| `mission_completed` | `int` | Running count of completed missions |
| `mission_redirected` | `int` | Running count of redirected missions |
| `body` | `str` or None | Body name after SupercruiseExit |
| `approach_body` | `str` or None | Body name during approach, cleared on LeaveBody |
| `dist_jumped` | `float` | Distance of last FSD jump (ly) |
| `jumps_remains` | `int` | Remaining jumps in plotted route |
| `fuel_capacity` | `float` or None | Main fuel tank capacity (tons) |
| `fuel_level` | `float` or None | Current fuel level (tons) |
| `fuel_percent` | `int` or None | Fuel level as percentage (0-100) |
| `is_scooping` | `bool` | True if actively fuel scooping and not full |
| `cur_star_system` | `str` | Current star system name |
| `cur_station` | `str` | Current station name |
| `cur_station_type` | `str` | Raw station type string from journal |
| `exp_station_type` | `StationType` | Parsed station type enum |
| `cargo_capacity` | `int` or None | Ship cargo capacity (tons) |
| `ship_size` | `str` or None | Ship landing pad size ('S', 'M', 'L') |
| `has_fuel_scoop` | `bool` or None | True if fuel scoop equipped |
| `SupercruiseDestinationDrop_type` | `str` or None | Type from SupercruiseDestinationDrop event |
| `has_adv_dock_comp` | `bool` or None | True if advanced docking computer equipped |
| `has_std_dock_comp` | `bool` or None | True if standard docking computer equipped |
| `has_sco_fsd` | `bool` or None | True if SCO FSD equipped |
| `StationServices` | `list` or None | List of station service strings |
| `ConstructionDepotDetails` | `dict` or None | Latest construction depot event data |
| `MarketID` | `int` | Market ID of current station |
| `last_market_buy` | `dict` or None | Last MarketBuy: `{Type, Count, timestamp}` |
| `last_market_sell` | `dict` or None | Last MarketSell: `{Type, Count, timestamp}` |
| `nav_route_cleared` | `bool` | True after NavRouteClear, False after NavRoute |

### Methods

| Method | Returns | Description |
|---|---|---|
| `__init__(cb)` | None | Init journal reader with callback. Opens latest journal, reads all existing entries, resets transient flags. |
| `get_file_modified_time()` | `float` | Returns OS modification timestamp of current journal file. |
| `reset_items()` | None | Clears transient flags: `under_attack` and `fighter_destroyed` set to False. Called after initial log read. |
| `get_latest_log(path_logs)` | `str` or None | Returns full path of latest `Journal.*` file by modification time. Uses Windows Saved Games path if `path_logs` not given. |
| `open_journal(log_name)` | None | Closes current journal file (if open) and opens the specified journal file for reading. Resets modification time tracker. |
| `_update_location(log, services_optional)` | None | Extracts location fields (StarSystem, StationName, StationType, StationServices, MarketID) from a journal event dict and updates ship state. Computes `exp_station_type` via `check_station_type()`. |
| `parse_line(log)` | None | Parses a single journal event dict. Handles: Fileheader, ShieldState, UnderAttack, FighterDestroyed, MissionCompleted, MissionRedirected, StartJump, SupercruiseEntry, FSDJump, DockingGranted, DockingDenied, SupercruiseExit, SupercruiseDestinationDrop, ApproachBody, LeaveBody, DockingCancelled, Undocked, DockingRequested, Docked, Location, Interdicted, LoadGame, Loadout, MarketBuy, MarketSell, FuelScoop, FSDTarget, NavRouteClear, NavRoute, CarrierJump, ColonisationConstructionDepot. Also processes fuel fields from any event. |
| `process_construction_depot_details()` | None | Compares current vs previous construction depot data. If changed, loads `configs/construction.json`, updates market entry with system/station/progress/resources, logs needed resources, saves file. |
| `ship_state()` | `dict` | Returns ship state dict. If file modification time unchanged, returns cached state. Otherwise tails the journal file, parsing new lines. Handles partial lines by buffering and retrying next call. |

## Journal Events Handled

| Event | Fields Updated |
|---|---|
| `Fileheader` | `odyssey` (hardset True) |
| `ShieldState` | `shieldsup` |
| `UnderAttack` | `under_attack` |
| `FighterDestroyed` | `fighter_destroyed` |
| `MissionCompleted` | `mission_completed` (incremented) |
| `MissionRedirected` | `mission_redirected` (incremented) |
| `StartJump` | `status`, `star_class`, `SupercruiseDestinationDrop_type` |
| `SupercruiseEntry` | `status`, `approach_body` |
| `FSDJump` | `status`, `location`, `cur_star_system`, `star_class`, `target`, `dist_jumped` |
| `DockingGranted` | `status` |
| `DockingDenied` | `status`, `no_dock_reason` |
| `SupercruiseExit` | `status`, `body` |
| `SupercruiseDestinationDrop` | `SupercruiseDestinationDrop_type` |
| `ApproachBody` | `approach_body` |
| `LeaveBody` | `approach_body` (cleared) |
| `DockingCancelled` | `status` |
| `Undocked` | `status` |
| `DockingRequested` | `status` |
| `Docked` | `status`, location fields via `_update_location` |
| `Location` | Location fields via `_update_location`, `status` if docked |
| `Interdicted` | `interdicted` |
| `LoadGame` | `type`, `ship_size` |
| `Loadout` | `type`, `ship_size`, `cargo_capacity`, `has_fuel_scoop`, `has_adv_dock_comp`, `has_std_dock_comp`, `has_sco_fsd` |
| `MarketBuy` | `last_market_buy` |
| `MarketSell` | `last_market_sell` |
| `FuelScoop` | `fuel_level`, `is_scooping` |
| `FSDTarget` | `target`, `jumps_remains` |
| `NavRouteClear` | `target`, `jumps_remains`, `nav_route_cleared` |
| `NavRoute` | `nav_route_cleared` (set False) |
| `CarrierJump` | Location fields via `_update_location` |
| `ColonisationConstructionDepot` | `ConstructionDepotDetails`, triggers `process_construction_depot_details()` |
| Any event with `FuelLevel` | `fuel_level`, `fuel_percent` |
| Any event with `FuelCapacity` | `fuel_capacity`, `fuel_percent` |

## Dependencies

| Module | Purpose |
|---|---|
| `EDAP_data` | `ship_size_map` and `ship_name_map` dictionaries |
| `EDlogger` | Logging via `logger` |
| `WindowsKnownPaths` | Locate Windows Saved Games folder for journal files |
| `json` | JSON parsing for journal lines and construction file I/O |
| `os` | File existence and modification time checks |
| `datetime` | Timestamp delta calculation at init |

## Notes

- Journal file is opened once and tailed; not re-read from scratch on each call
- Partial JSON lines (mid-write by game) are buffered and joined on next read
- Lines not starting with '{' are skipped as fragments
- `fuel_percent` defaults to 10 when fuel data unavailable
- `is_scooping` only True during FuelScoop events when tank not full
- `odyssey` is hardset to True for ED 4.0 since menus are the same for Horizons
- SRV (TestBuggy) fuel data is ignored
