# src/ed/EDJournal.py (641 lines)

Threaded journal file processor. Opens the latest `Journal*.log` file, catches up
on existing entries at startup, then continuously tails new lines in a background
daemon thread.

## Threading Model

- `_catchup()` runs in `__init__` on the calling thread (reads existing file)
- `start()` launches a daemon thread running `_tail_loop()`
- `_tail_loop()` polls every 200ms for new lines, checks journal rotation every 5s
- `stop()` signals the thread to exit and joins

## Event System

```python
jn.on_event('Loadout', callback)      # register listener
jn.on_event('_fuel_update', callback)  # synthetic event
```

`_fire_event(event_name, log)` calls all registered callbacks for that event.
Callbacks receive the parsed journal log dict.

### Synthetic Events

| Event | Fires When |
|-------|------------|
| `_fuel_update` | Any line with `FuelLevel`, `FuelCapacity`, or event `FuelScoop` |
| `ColonisationConstructionDepot` | Depot details event parsed |

## Key Methods

| Method | Description |
|--------|-------------|
| `ship_state()` | Pure getter, returns cached `self.ship` dict (no I/O) |
| `set_field(key, value)` | Thread-safe write to ship dict (uses lock) |
| `on_event(name, cb)` | Register event callback |
| `start()` / `stop()` | Manage background thread |
| `parse_line(log)` | Process one journal event dict |
| `_try_parse(line, partial)` | Static: JSON parse with incomplete-line defense |

## Ship State Dict

`ship_state()` returns a dict with navigation/mission fields:

| Key | Updated By |
|-----|-----------|
| `type` | LoadGame, Loadout |
| `status` | Various (in_space, in_supercruise, docked, etc.) |
| `target` | FSDTarget |
| `jumps_remains` | FSDTarget, external set_field |
| `location`, `cur_star_system`, `cur_station` | Location, FSDJump, Docked |
| `music_track` | Music |
| `interdicted`, `under_attack`, `fighter_destroyed` | Events |
| `nav_route_cleared` | NavRouteClear |
| `StarClass` | FSDJump |
| `body`, `approach_body` | ApproachBody, external |

Ship-property fields (fuel, modules) also live here for backward compat but
Ship owns the canonical copies via event callbacks.

## Module-Level Functions

| Function | Description |
|----------|-------------|
| `get_ship_size(ship)` | Returns 'S'/'M'/'L' from journal ship name |
| `get_ship_fullname(ship)` | Returns display name from journal ship name |
| `_has_module(modules, item, slot)` | Check if module list contains item |
| `check_fuel_scoop(modules)` | Has fuel scoop? |
| `check_adv_docking_computer(modules)` | Has advanced dock comp? |
| `check_std_docking_computer(modules)` | Has standard dock comp? |
| `check_sco_fsd(modules)` | Has SCO FSD? (slot must be FrameShiftDrive) |
| `check_station_type(type, name, services)` | Returns StationType enum |

## StationType Enum

```
Unknown, Starport, Outpost, FleetCarrier, SquadronCarrier,
ColonisationShip, SpaceConstructionDepot, PlanetaryConstructionDepot, SurfaceStation
```

## Incomplete Line Defense

`_tail_loop` reads to EOF. If the last line doesn't end with `\n`, it seeks back
(the game may still be writing). `_try_parse` catches JSON decode errors and
optionally joins a partial line with the next read.

## Dependencies

- `src.core.EDAP_data` -- ship_size_map, ship_name_map
- `src.core.EDlogger` -- logger
- `src.core.WindowsKnownPaths` -- journal directory path
