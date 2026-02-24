# EDBob Architecture

## Overview

EDBob is an Elite Dangerous autopilot that combines screen capture (compass/target
reading via OpenCV) with game file parsing (journal, status.json, navroute, cargo,
market) and DirectInput key injection to automate flight, docking, and trade routes.

## Layers

```
  GUI (EDBob.py)
    |
  Autopilot (ED_AP.py, EDWayPoint.py)
    |
  +--------+----------+------------------+
  |        |          |                  |
 Ship   Journal   Screen/Vision    Game File Parsers
  |        |          |                  |
  +--------+----+-----+------------------+
                |
          Core (logging, constants, DirectInput, paths)
```

### GUI Layer -- `src/gui/EDBob.py`

Tkinter application. Creates a single `EDAutopilot` instance at startup.
Provides checkboxes/buttons to enable assists, displays status via callbacks.
Hotkeys: Home=FSD, Insert=SC, End=Stop.

The GUI runs on the main thread. Assists run on a separate engine thread.

### Autopilot Layer -- `src/autopilot/`

**ED_AP.py** -- Central controller. Owns all subsystems (journal, ship, screen,
keys, parsers, panel readers). Runs `engine_loop()` on a background thread that
dispatches to active assists (SC assist, waypoint assist, DSS, calibration).
Each assist is blocking -- the loop re-checks after completion.

Decision-maker only. Does NOT send keys directly for ship movement -- delegates
angles to Ship which handles timing and key selection.

**EDWayPoint.py** -- Loads waypoint JSON files (trade routes, exploration routes).
Tracks step progress, manages station service interactions (buy/sell/refuel).

### Ship Layer -- `src/ship/Ship.py`

Represents the physical vessel. Owns:
- **Identity**: ship_type, ship_size (from journal events)
- **Modules**: has_fuel_scoop, has_adv_dock_comp, has_std_dock_comp, has_sco_fsd
- **Fuel**: fuel_level, fuel_capacity, fuel_percent, is_scooping
- **Turn rates**: pitchrate, rollrate, yawrate (per flight mode)
- **Flight mode**: normal vs supercruise, auto-switches via status.json flags
- **Movement**: send_pitch(), send_roll(), hold_time() -- Ship picks rate and key
- **Calibration**: measures turn rates, persists per-ship per-mode configs

Ship registers journal event callbacks (`register_journal_events(jn)`) and
syncs from journal catchup at startup. Live events (LoadGame, Loadout, FuelScoop)
keep properties current.

### Journal -- `src/ed/EDJournal.py`

Background daemon thread tailing the active journal file. Polls every 200ms,
detects journal rotation every 5s. Fires event callbacks via `on_event()`.

Key design points:
- `_catchup()` reads existing file at init (before thread starts)
- `ship_state()` is a pure getter (no I/O)
- `set_field(key, value)` for thread-safe external writes
- `_try_parse()` handles incomplete JSON lines (seek-back defense)
- Synthetic `_fuel_update` event fires for any line with FuelLevel/FuelCapacity

### Screen/Vision -- `src/screen/`

**Screen.py** -- Low-level mss screen capture + win32gui window management.
Captures regions, applies HSV color filters, returns masked images.

**Screen_Regions.py** -- Region definitions (compass, target, sun, nav panel, etc.)
with resolution-independent `Point` and `Quad` geometry classes. HSV filter configs
for orange (compass dot), blue (target), cyan (station markers).

### Game File Parsers -- `src/ed/`

| Parser | File | Purpose |
|--------|------|---------|
| StatusParser | status.json | Real-time flags, pips, fuel, gui focus |
| NavRouteParser | NavRoute.json | Current plotted route |
| CargoParser | Cargo.json | Ship inventory |
| MarketParser | Market.json | Station commodity prices |
| EDGraphicsSettings | DisplaySettings.xml | FOV, resolution |
| EDKeys | *.binds | Key bindings |

### Panel Readers -- `src/ed/`

Screen-scrape the in-game UI panels:

| Reader | Panel | Used For |
|--------|-------|----------|
| EDNavigationPanel | Left panel | Target selection, docking requests |
| EDInternalStatusPanel | Right panel | Module status |
| EDGalaxyMap | Galaxy map | Route plotting via bookmarks |
| EDSystemMap | System map | Destination selection |
| EDStationServicesInShip | Station services | Refuel, repair, commodities |
| EDShipControl | Cockpit | Flight mode transitions |
| MenuNav | All menus | Stateless menu navigation functions |

### Core -- `src/core/`

| Module | Purpose |
|--------|---------|
| EDlogger | Rotating file + console logging (colorlog) |
| EDAP_data | Status flag constants, ship size/name maps |
| constants | Version string, form type enums, window title |
| directinput | Windows DirectInput key simulation via ctypes |
| WindowsKnownPaths | Windows known folder path resolution |

## Threading Model

```
Main Thread          Engine Thread         Journal Thread
(tkinter GUI)        (assist loop)         (file tail)
     |                    |                     |
     |-- creates AP ----->|                     |
     |                    |-- creates journal -->|
     |                    |                     |-- polls 200ms
     |                    |-- runs assists      |-- fires events
     |<-- callbacks ------|                     |
     |                    |<-- ship updates ----|
```

- **Main thread**: GUI event loop. Callbacks from engine thread update UI via
  tkinter's thread-safe `after()`.
- **Engine thread**: Runs `engine_loop()`. Dispatches one assist at a time
  (blocking). Checks status.json every iteration for flight mode updates.
- **Journal thread**: Daemon thread. Tails journal file, fires event callbacks.
  Ship and ED_AP register listeners.

## Data Flow: Ship Properties

```
Journal file --> EDJournal (parse) --> event callbacks --> Ship (owns properties)
                                                            |
ED_AP reads Ship.has_fuel_scoop, Ship.fuel_percent, etc. <-+
```

Ship syncs from journal catchup at startup, then stays current via live events.
ED_AP never reads journal for ship-property fields -- always asks Ship.

Navigation/mission state (target, status, station, route) stays on EDJournal.
ED_AP reads those via `jn.ship_state()`.

## Data Flow: Movement

```
ED_AP decides angle --> Ship.send_pitch(deg) --> Ship picks key + rate --> EDKeys.send()
                                                      |
                                        flight mode (normal/SC) determines rate
                                        zero-throttle factor applied if needed
```

## Config Files

| File | Purpose |
|------|---------|
| configs/AP.json | Autopilot settings (assists, thresholds) |
| configs/ship_configs.json | Per-ship turn rates (normal + SC) |
| configs/ocr_calibration.json | Screen region calibration |
| configs/construction.json | Colonisation construction depot data |

## Entry Point

`start_ed_ap.bat` creates a venv and runs `python -m src.gui.EDBob`.
