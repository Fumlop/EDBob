# CargoParser.py -- Cargo.json Parser

## Purpose

Parses the Elite Dangerous `Cargo.json` file to read current ship cargo inventory. Provides item lookup by name and inventory listing.
Lives in `src/ed/CargoParser.py`.

## Class: CargoParser

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `file_path` | str or None | Custom path to Cargo.json. Auto-detects on Windows (SavedGames) and Linux (`./linux_ed/`). |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `file_path` | str | Absolute path to Cargo.json |
| `last_mod_time` | float or None | Last known file modification timestamp |
| `current_data` | dict or None | Latest parsed cargo data |

### Cargo.json Format

```json
{
  "timestamp": "2025-04-20T23:23:25Z",
  "event": "Cargo",
  "Vessel": "Ship",
  "Count": 0,
  "Inventory": [
    {"Name": "cmmcomposite", "Name_Localised": "CMM Composite", "Count": 1236, "Stolen": 0}
  ]
}
```

### Methods

| Method | Returns | Description |
|---|---|---|
| `get_file_modified_time()` | float | Returns OS file modification timestamp. |
| `wait_for_file_change(start_timestamp, timeout=5)` | bool | Block until Cargo.json internal timestamp changes. Polls every 0.5s. |
| `get_cargo_data()` | dict | Read Cargo.json if modified, return parsed data. Uses exponential backoff (1s start, 2x) on read failure. |
| `get_item(item_name)` | dict or None | Get details of one item by name (case-insensitive). Matches against both `Name` and `Name_Localised`. Does NOT trigger a file re-read. Returns item dict or None. |
| `get_items()` | list | Get all items in cargo inventory. Does NOT trigger a file re-read. Returns the `Inventory` list. |

### Item Dict Format

```json
{"Name": "cmmcomposite", "Name_Localised": "CMM Composite", "Count": 1236, "Stolen": 0}
```

Note: `Name_Localised` is optional in some items.

## Dependencies

| Module | Purpose |
|---|---|
| `EDlogger` | Logging |
| `WindowsKnownPaths` | SavedGames path resolution (Windows) |

## Notes

- File change detection uses OS modification time (fast path)
- `get_item()` matches case-insensitively against both internal name and localized name
- `get_item()` and `get_items()` use cached data (no file re-read)
- Read retry uses exponential backoff starting at 1s
- Handles both Windows and Linux paths
