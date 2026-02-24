# Small Modules

## src/core/constants.py (15 lines)

App-wide constants:
- `EDAP_VERSION = "V1.3.0"`
- `FORM_TYPE_CHECKBOX`, `FORM_TYPE_SPINBOX`, `FORM_TYPE_ENTRY`
- `ED_WINDOW_TITLE = "Elite - Dangerous (CLIENT)"`

## src/core/EDlogger.py (47 lines)

Centralized logging setup. Creates a `colorlog` logger with:
- Console: WARNING level
- File: `autopilot.log`, 10MB rotating, 5 backups

Exports: `logger` (used by all modules)

## src/core/directinput.py (346 lines)

Windows DirectInput key simulation via ctypes. Defines `SCANCODE` dict mapping
key names to scan codes. Provides `SendInput` wrapper for keystroke injection.

## src/core/WindowsKnownPaths.py (164 lines)

Windows known folder path resolution via `SHGetKnownFolderPath` COM API.
Used to find ED's SavedGames and LocalAppData directories.

Key export: `get_path(FOLDERID, UserHandle)` -> str

## src/ed/EDGraphicsSettings.py (33 lines)

Reads ED graphics XML config for screen resolution and FOV.
Properties: `screenwidth`, `screenheight`, `fov`

## src/ed/NavRouteParser.py (106 lines)

Parses `NavRoute.json` (current plotted route).
Key method: `get_nav_route_data()` -> list of route entries

## src/ed/CargoParser.py (114 lines)

Parses `Cargo.json` (ship inventory).
Key methods: `get_cargo_data()`, `wait_for_file_change()`

## src/ed/MarketParser.py (282 lines)

Parses `Market.json` (station commodity prices).
Key method: `get_market_data()` -> market dict

## src/ed/EDGalaxyMap.py (221 lines)

Galaxy map UI interaction. Sets destinations via bookmarks.
Key method: `set_gal_map_dest_bookmark(type, position)`

## src/ed/EDSystemMap.py (117 lines)

System map UI interaction. Sets destinations via bookmarks.
Key method: `set_sys_map_dest_bookmark(type, position)`

## src/ed/EDInternalStatusPanel.py (338 lines)

Right-hand ship status panel reader. Tab navigation, perspective deskewing.
Uses `EDNavigationPanel` perspective transform utilities.

## src/ed/EDShipControl.py (20 lines)

Minimal flight mode control. Key method: `goto_cockpit_view()`
