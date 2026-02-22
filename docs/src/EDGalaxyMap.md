# EDGalaxyMap.py -- Galaxy Map Controller

## Purpose

Manages the Galaxy Map interface for setting navigation destinations via text search, bookmarks, or OCR-based favorites selection. Supports both Odyssey and Horizons game versions. Lives in `src/ed/EDGalaxyMap.py`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `_get_ocr_reader()` | `easyocr.Reader` | Lazy-load singleton EasyOCR reader (English, CPU-only). Heavy init, created once. |

## Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `FAV_LIST_REGION_PCT` | `[0.076, 0.172, 0.215, 0.522]` | Favorites list text region as fraction of screen `[L, T, R, B]`. Sized for 1440x900 game window. Excludes icon sidebar. |

## Class: EDGalaxyMap

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | ED_AP | Reference to main autopilot instance |
| `screen` | Screen | Screen capture interface |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback for status messages |
| `is_odyssey` | bool | True for Odyssey, False for Horizons (default True) |

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | ED_AP | Reference to main autopilot |
| `is_odyssey` | bool | Game version flag |
| `screen` | Screen | Screen capture interface |
| `keys` | EDKeys | Key sending interface |
| `status_parser` | StatusParser | GUI focus state detection |
| `ap_ckb` | callable | GUI callback |
| `reg` | dict | Screen regions: `full_panel`, `cartographics`, `fav_list` |
| `SystemSelectDelay` | float | Delay for system selection in galaxy map (0.5s default) |

### Favorites OCR Methods

| Method | Returns | Description |
|---|---|---|
| `_ocr_favorites_list()` | `list[tuple[int, str, int]]` | OCR the visible favorites list. Isolates white text via HSV mask, parses `-N-NAME` pattern. Returns list of `(number, name, y_position)` sorted top to bottom. |
| `_open_favorites_panel()` | `bool` | Open galaxy map and navigate to the FAVOURITES bookmark list. Returns True if successful. |
| `select_favorite_by_number(target_number)` | `bool` | Open galaxy map favorites, OCR the list, navigate to the entry matching `target_number`, long-press select to plot route. Accounts for non-numbered items above target using Y-position counting. Closes galaxy map when done. |
| `get_available_favorites()` | `list[int]` | Return list of waypoint numbers found in the currently visible favorites list. Requires favorites panel already open. |

### Legacy Bookmark/Text Methods

| Method | Returns | Description |
|---|---|---|
| `set_gal_map_dest_bookmark(ap, bookmark_type, bookmark_position)` | `bool` | Set destination using a bookmark. Supports types: Favorite, System, Body, Station, Settlement. Navigates UI to correct bookmark category and position. Odyssey only. |
| `set_gal_map_destination_text(ap, target_name, target_select_cb)` | `bool` | Delegates to Odyssey or Horizons text search implementation based on `is_odyssey` flag. |
| `set_gal_map_destination_text_horizons(ap, target_name, target_select_cb)` | `bool` | Horizons version: types system name via pyautogui, sends enter, selects result. Optionally waits for `target_select_cb` confirmation. |
| `set_gal_map_destination_text_odyssey(ap, target_name)` | `bool` | Odyssey version: types system name, searches, validates nav route matches target. Retries with UI_Up if wrong system selected. Checks NavRouteParser for route confirmation. |
| `set_next_system(ap, target_system)` | `bool` | Wrapper: calls `set_gal_map_destination_text` for the given target system. |

### Galaxy Map Navigation

| Method | Returns | Description |
|---|---|---|
| `goto_galaxy_map()` | `bool` | Open Galaxy Map if not already open. Waits for `GuiFocusGalaxyMap` via StatusParser (15s timeout). Navigates cursor to search bar. Shows debug overlay if enabled. If already open, resets cursor position. |

## Screen Regions

| Region Key | Default Rect | Description |
|---|---|---|
| `full_panel` | `[0.1, 0.1, 0.9, 0.9]` | Full galaxy map panel area |
| `cartographics` | `[0.0, 0.0, 0.15, 0.15]` | Top-left cartographics indicator |
| `fav_list` | `FAV_LIST_REGION_PCT` | Favorites list text column |

Regions can be overridden via `load_calibrated_regions('EDGalaxyMap', ...)`.

## Dependencies

| Module | Purpose |
|---|---|
| `cv2` / `numpy` | HSV color filtering for OCR preprocessing |
| `easyocr` | Optical character recognition for favorites list |
| `re` | Regex parsing of `-N-NAME` pattern |
| `StatusParser` | GUI focus state detection (`GuiFocusGalaxyMap`) |
| `Screen_Regions` | `scale_region`, `Quad`, `load_calibrated_regions` |
| `EDAP_data` | `GuiFocusGalaxyMap` constant |
| `EDlogger` | Logging |
| `pyautogui` | Text input via `typewrite()` (imported inside methods) |

## Notes

- Favorites OCR isolates white text (HSV: S<=60, V>=160) to ignore orange subtitle text
- Naming convention for favorites: `-N-NAME` where N is the waypoint number (1, 2, 3...)
- Items prefixed with `0-` are excluded from waypoint selection (e.g. `0-HOMECARRIER`)
- EasyOCR reader is lazy-loaded as a module-level singleton to avoid repeated heavy initialization
- Validates nav route changes in Odyssey text search to confirm correct destination was selected
- Uses UI navigation keys throughout (UI_Up, UI_Down, UI_Left, UI_Right, UI_Select)
