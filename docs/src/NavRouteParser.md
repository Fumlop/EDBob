# NavRouteParser.py -- NavRoute.json Parser

## Purpose

Parses the Elite Dangerous `NavRoute.json` file to read the plotted hyperspace route. Provides access to route data and final destination system name.
Lives in `src/ed/NavRouteParser.py`.

## Class: NavRouteParser

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `file_path` | str or None | Custom path to NavRoute.json. Auto-detects on Windows (SavedGames) and Linux (`./linux_ed/`). |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `file_path` | str | Absolute path to NavRoute.json |
| `last_mod_time` | float or None | Last known file modification timestamp |
| `current_data` | dict or None | Latest parsed route data |

### NavRoute.json Format

When route is active:
```json
{
  "timestamp": "...", "event": "NavRoute",
  "Route": [
    {"StarSystem": "Leesti", "SystemAddress": 123, "StarPos": [x,y,z], "StarClass": "K"},
    ...
  ]
}
```

When route is cleared:
```json
{"timestamp": "...", "event": "NavRouteClear", "Route": []}
```

### Methods

| Method | Returns | Description |
|---|---|---|
| `get_file_modified_time()` | float | Returns OS file modification timestamp. |
| `get_nav_route_data()` | dict or None | Read NavRoute.json if modified, return parsed data. Returns None if file does not exist. Uses exponential backoff (1s start, 2x) on read failure. |
| `get_last_system()` | str | Returns the final destination system name from the route. Returns empty string if no route, route cleared, or route is None. |

## Dependencies

| Module | Purpose |
|---|---|
| `EDlogger` | Logging |
| `WindowsKnownPaths` | SavedGames path resolution (Windows, imported conditionally) |

## Notes

- First entry in Route array is the starting (current) system
- Last entry is the final destination
- File change detection uses OS modification time (fast path)
- Read retry uses exponential backoff starting at 1s
- Handles both Windows and Linux paths
- Standalone `__main__` block polls `get_last_system()` every second
