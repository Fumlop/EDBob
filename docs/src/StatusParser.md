# StatusParser.py -- Status.json Parser

## Purpose

Parses the Elite Dangerous `Status.json` file to extract and translate game state flags, fuel, cargo, position, and destination information. Provides flag querying and blocking wait-for-state methods.
Lives in `src/ed/StatusParser.py`.

## Class: StatusParser

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `file_path` | str or None | Custom path to Status.json. Auto-detects on Windows (SavedGames) and Linux (`./linux_ed/`). |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `file_path` | str | Absolute path to Status.json |
| `last_mod_time` | float or None | Last known file modification timestamp |
| `current_data` | dict or None | Latest cleaned data |
| `last_data` | dict or None | Previous cleaned data (for diff detection) |

### Cleaned Data Fields

| Field | Type | Description |
|---|---|---|
| `time` | str | Current time + 469711 days (in-game year) |
| `timestamp` | datetime | Parsed timestamp from Status.json |
| `timestamp_delta` | float | Seconds between consecutive updates |
| `Flags` | int | Primary status flags bitmask |
| `Flags2` | int or None | Secondary status flags bitmask |
| `Pips` | dict or None | `{system, engine, weapons}` (halved values) |
| `GuiFocus` | int or None | Current GUI focus panel ID |
| `Cargo` | float or None | Current cargo tonnage |
| `LegalState` | str or None | Legal status (e.g. "Clean") |
| `Latitude` / `Longitude` | float or None | Surface position |
| `Heading` / `Altitude` | float or None | Surface heading and altitude |
| `PlanetRadius` | float or None | Nearby planet radius |
| `Balance` | int or None | Credit balance |
| `Destination_System` | str | Destination system ID |
| `Destination_Body` | int | Destination body number (0 = main star) |
| `Destination_Name` | str | Destination name |
| `FuelMain` / `FuelReservoir` | float or None | Fuel levels |

### Flag Definitions

Class-level lists `_FLAGS1_DEFS` and `_FLAGS2_DEFS` define all 32 bits for each flag register. Key flags:

| Bit | Flags1 Name |
|---|---|
| 1 | Docked |
| 2 | Landed |
| 16 | Supercruise |
| 65536 | Fsd MassLocked |
| 131072 | Fsd Charging |
| 1073741824 | Fsd Jump |

| Bit | Flags2 Name |
|---|---|
| 524288 | Fsd hyperdrive charging |
| 1048576 | FSD SCO Active |

### Methods

| Method | Returns | Description |
|---|---|---|
| `get_file_modified_time()` | float | Returns OS file modification timestamp. |
| `get_cleaned_data()` | dict | Read Status.json if modified, parse and return cleaned data. Uses exponential backoff on read failure. |
| `wait_for_file_change(start_timestamp, timeout=5)` | bool | Block until Status.json internal timestamp changes. Polls every 0.5s. |
| `translate_flags(flags_value)` | dict | Convert Flags integer to dict of True flag names only. |
| `translate_flags2(flags2_value)` | dict | Convert Flags2 integer to dict of True flag names only. |
| `transform_pips(pips_list)` | dict | Convert `[sys, eng, wep]` array to `{system, engine, weapons}` dict with halved values. |
| `adjust_year(timestamp)` | str | Add 1286 years to timestamp string (game year conversion). |
| `log_flag_diffs()` | None | Print flag state changes between `last_data` and `current_data`. Covers both Flags and Flags2. |
| `get_gui_focus()` | int | Get current GUI focus value. Triggers data refresh. |
| `wait_for_gui_focus(gui_focus_flag, timeout=15)` | bool | Block until GuiFocus matches. Polls every 0.5s. |
| `wait_for_flag_on(flag, timeout=15)` | bool | Block until Flags1 bit becomes True. |
| `wait_for_flag_off(flag, timeout=15)` | bool | Block until Flags1 bit becomes False. |
| `wait_for_flag2_on(flag, timeout=15)` | bool | Block until Flags2 bit becomes True. Returns False if Flags2 not present. |
| `wait_for_flag2_off(flag, timeout=15)` | bool | Block until Flags2 bit becomes False. Returns False if Flags2 not present. |
| `get_flag(flag)` | bool | Get current value of Flags1 bit. Triggers data refresh. |
| `get_flag2(flag)` | bool | Get current value of Flags2 bit. Triggers data refresh. Returns False if Flags2 is None. |

## Dependencies

| Module | Purpose |
|---|---|
| `EDAP_data` | Flag constants referenced by callers |
| `EDlogger` | Logging |
| `WindowsKnownPaths` | SavedGames path resolution (Windows only) |

## Notes

- File change detection uses OS modification time check first (fast path), only reads JSON on change
- Read retry uses exponential backoff starting at 0.1s with 2x multiplier
- `_translate_flags` is a static helper; returns only True flags (sparse dict)
- Handles both Windows and Linux paths transparently
- Timestamp delta tracks seconds between consecutive Status.json updates
- Standalone `__main__` block runs continuous flag diff monitoring
