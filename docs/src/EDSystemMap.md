# EDSystemMap.py -- System Map Navigation

## Purpose

Manages the System Map interface for setting local destinations via bookmarks.
Supports Odyssey with special handling for Nav Panel bookmark types.
Lives in `src/ed/EDSystemMap.py`.

## Class: EDSystemMap

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `screen` | Screen | Screen capture instance |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback |
| `is_odyssey` | bool | Game version flag (default True) |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Parent reference |
| `is_odyssey` | bool | True for Odyssey, False for Horizons |
| `screen` | Screen | Screen capture |
| `keys` | EDKeys | Key sender |
| `status_parser` | StatusParser | Status.json reader |
| `ap_ckb` | callable | GUI callback |
| `reg` | dict | Screen regions: `full_panel`, `cartographics` (loaded from calibration file) |

### Methods

| Method | Returns | Description |
|---|---|---|
| `set_sys_map_dest_bookmark(ap, bookmark_type, bookmark_position)` | bool | Set destination via bookmark. Supports types: Favorite (default), Body, Station, Settlement, Navigation. Navigation type uses nav panel directly instead of system map. Returns False if not Odyssey or position is -1. |
| `goto_system_map()` | bool | Opens System Map if not already open. Waits for `GuiFocusSystemMap` (15s timeout). If already open, resets cursor position. Shows debug overlay if enabled. |

### Bookmark Type Navigation

| Type Prefix | UI_Down Count | Target |
|---|---|---|
| `fav` | 0 | Favorites (default, first item) |
| `bod` | 1 | Bodies |
| `sta` | 2 | Stations |
| `set` | 3 | Settlements |
| `nav` | N/A | Uses Nav Panel directly (not System Map) |

## Dependencies

| Module | Purpose |
|---|---|
| `StatusParser` | GUI focus detection (`GuiFocusSystemMap`) |
| `Screen_Regions` | `scale_region`, `Quad`, `load_calibrated_regions` |
| `EDAP_data` | `GuiFocusSystemMap` constant |
| `EDlogger` | Logging |

## Notes

- Nav panel bookmark type bypasses system map entirely, using left panel key sequences
- Bookmark position is 1-based (first bookmark = 1)
- Includes workaround for first bookmark not always being pre-selected (UI_Left + UI_Right)
- Uses `UI_Select` with 3.0s hold for system map bookmark confirmation
