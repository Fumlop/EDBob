# Screen_Regions.py -- Screen Region Capture and Geometry

## Purpose

Defines named screen regions for Elite Dangerous interface capture, provides image filtering
(color, threshold, equalization), and includes geometric helper classes (Point, Quad) for
rectangle/quadrilateral manipulation. Lives in `src/screen/Screen_Regions.py`.

## Architecture

- `Screen_Regions` class owns a dictionary of named regions, each with a capture rect and
  an optional filter callback. Regions are loaded from JSON config files per resolution
  (and optionally per ship type).
- A static `_REGION_FILTERS` dict maps region names to their filter method and HSV color range.
- `Point` and `Quad` are standalone geometry classes used for coordinate math throughout the project.
- OCR calibration data is managed separately via `load_ocr_calibration_data()`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `scale_region(region_rect, sub_region_rect)` | `[float, float, float, float]` | Converts a sub-region (percentage-based) to absolute coordinates within a parent region. Uses `Quad.subregion_from_quad()` internally. |
| `load_calibrated_regions(prefix, reg)` | None | Reads `configs/ocr_calibration.json` and overwrites matching region rects in `reg` dict. Handles sub-region scaling. Modifies `reg` in place. |
| `load_ocr_calibration_data()` | `dict[str, MyRegion]` | Loads or creates `configs/ocr_calibration.json` with default region definitions. Adds missing keys on load and saves back if updated. |

## TypedDicts

| TypedDict | Fields | Description |
|---|---|---|
| `SubRegion` | `rect: list[float]`, `text: str` | A sub-region within a calibration region |
| `Objects` | `width: float`, `height: float`, `text: str` | Object size definition for calibration |
| `MyRegion` | `rect: list[float]`, `text: str`, `readonly: bool`, `regions: dict`, `objects: dict` | Full calibration region entry |

## Screen_Regions Class

### Constructor

| Method | Returns | Description |
|---|---|---|
| `__init__(screen, ship_type=None)` | None | Stores screen reference, initializes HSV color ranges and sun threshold, calls `_load_regions()` to populate `self.reg` from JSON config. |

### Region Loading

| Method | Returns | Description |
|---|---|---|
| `_load_regions(ship_type=None)` | None | Loads regions from `configs/screen_regions/res_{W}_{H}/{ship_type}.json` (falls back to `default.json`). Builds `self.reg` dict with rect, width, height, filterCB, and filter for each named region. Sets `self.regions_loaded`. |
| `reload_regions(ship_type=None)` | None | Re-calls `_load_regions()`. Used when ship type changes. |

### Capture Methods

| Method | Returns | Description |
|---|---|---|
| `capture_region(screen, region_name, inv_col=True)` | ndarray | Grabs unfiltered screenshot of the named region via `screen.get_screen_region()`. |
| `capture_region_filtered(screen, region_name, inv_col=True)` | ndarray | Grabs screenshot, then applies the region's filter callback (if any). Returns raw image if no filter is assigned. |

### Filter Methods

| Method | Returns | Description |
|---|---|---|
| `equalize(image, noOp)` | ndarray (grayscale) | Converts to grayscale, applies CLAHE histogram equalization (clipLimit=2.0, tileGridSize=8x8). Used for compass, missions, nav_panel, mission_dest regions. |
| `filter_by_color(image, color_range)` | ndarray (binary mask) | Converts BGR to HSV, applies `cv2.inRange()` with given color range. Returns binary mask (white=match, black=no match). |
| `filter_bright(image, noOp)` | ndarray (binary mask) | Equalizes then filters for high-value pixels only (V: 215-255). Currently unused (marked "not used"). |
| `filter_sun(image, noOp)` | ndarray (binary B&W) | Converts to grayscale, applies binary threshold at `self.sun_threshold`. Used for star/sun detection. |

### Sun Detection

| Method | Returns | Description |
|---|---|---|
| `set_sun_threshold(thresh)` | None | Sets the brightness threshold for sun detection (default: 125). |
| `sun_percent(screen)` | int | Captures the `sun` region filtered, counts white vs black pixels, returns percentage of white (0-100). |

### Region Filter Map (`_REGION_FILTERS`)

| Region Name | Filter Method | Color Range |
|---|---|---|
| `compass` | `equalize` | None |
| `target` | `filter_by_color` | `orange_2_color_range` |
| `sun` | `filter_sun` | None |
| `disengage` | `filter_by_color` | `blue_sco_color_range` |
| `sco` | `filter_by_color` | `blue_sco_color_range` |
| `sc_assist_ind` | `filter_by_color` | `cyan_sc_assist_range` |
| `mission_dest` | `equalize` | None |
| `missions` | `equalize` | None |
| `nav_panel` | `equalize` | None |
| `center_text` | `filter_by_color` | `orange_color_range` |

### HSV Color Ranges

| Attribute | Low | High | Used For |
|---|---|---|---|
| `orange_color_range` | `[0, 130, 123]` | `[25, 235, 220]` | Center text detection |
| `orange_2_color_range` | `[16, 165, 220]` | `[98, 255, 255]` | Target circle detection |
| `blue_color_range` | `[0, 28, 170]` | `[180, 100, 255]` | (Defined but not mapped to any region) |
| `blue_sco_color_range` | `[10, 0, 0]` | `[100, 150, 255]` | Disengage button, SCO text |
| `cyan_sc_assist_range` | `[80, 80, 80]` | `[110, 255, 255]` | SC Assist indicator |

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `screen` | Screen | Screen capture object reference |
| `regions_loaded` | bool | True if regions were successfully loaded from config |
| `sun_threshold` | int | Brightness threshold for sun filter (default: 125) |
| `reg` | dict | Dict of region definitions keyed by name. Each value has `rect`, `width`, `height`, `filterCB`, `filter`. |

## Point Class

Represents a 2D coordinate.

| Method | Returns | Description |
|---|---|---|
| `__init__(x, y)` | None | Create point with x, y coordinates |
| `get_x()` | float | Returns x coordinate |
| `get_y()` | float | Returns y coordinate |
| `to_list()` | `[float, float]` | Returns `[x, y]` list |
| `from_xy(xy_tuple)` | Point | Class method: create from `(x, y)` tuple |
| `from_list(xy_list)` | Point | Class method: create from `[x, y]` list |
| `__str__()` | str | String representation `"Point(x, y)"` |

## Quad Class

Represents a quadrilateral defined by four `Point` objects. Assumes rectangular geometry for
subregion operations.

### Constructors

| Method | Returns | Description |
|---|---|---|
| `__init__(p1, p2, p3, p4)` | None | Create from four Point objects (all optional, default None) |
| `from_list(pt_list)` | Quad | Class method: create from `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]` |
| `from_rect(pt_list)` | Quad | Class method: create from `[left, top, right, bottom]` |

### Accessors

| Method | Returns | Description |
|---|---|---|
| `to_rect_list(round_dp=-1)` | `[float, float, float, float]` | Bounds as `[left, top, right, bottom]`. Rounds to `round_dp` decimal places if >= 0. |
| `to_list()` | `[[float,float], ...]` | Four points as list of `[x, y]` pairs |
| `get_left()` | float | Minimum x across all points |
| `get_top()` | float | Minimum y across all points |
| `get_right()` | float | Maximum x across all points |
| `get_bottom()` | float | Maximum y across all points |
| `get_width()` | float | `right - left` |
| `get_height()` | float | `bottom - top` |
| `get_top_left()` | Point | Top-left corner (copy) |
| `get_bottom_right()` | Point | Bottom-right corner (copy) |
| `get_bounds()` | `(Point, Point)` | Bounding rect as `(top_left, bottom_right)` |
| `get_center()` | Point | Average of all four points |

### Transformations

| Method | Returns | Description |
|---|---|---|
| `scale(fx, fy)` | None | Scale from center by factors fx, fy. Modifies in place. |
| `inflate(x, y)` | None | Expand outward from center by x, y amounts. Points closer to center than the center move inward. |
| `subregion_from_quad(quad)` | None | Crop to percentage-based sub-region (0.0-1.0). E.g. `[0, 0, 0.25, 0.25]` = top-left quarter. Modifies in place. |
| `scale_from_origin(fx, fy)` | None | Scale from origin (0,0) by factors fx, fy. Modifies in place. |
| `offset(dx, dy)` | None | Translate by dx, dy. Modifies in place. |

### Static Helpers

| Method | Returns | Description |
|---|---|---|
| `_scale_point(pt, center, fx, fy)` | Point | Scale a point relative to a center |
| `_inflate_point(pt, center, x, y)` | Point | Inflate a point outward from center |
| `_offset_point(pt, dx, dy)` | Point | Offset a point (uses new Point for shallow copy safety) |

## OCR Calibration Data

`load_ocr_calibration_data()` manages default region definitions for various UI panels. Stored
in `configs/ocr_calibration.json`. Default entries cover:

| Key Prefix | Description |
|---|---|
| `EDCodex` | Codex panel bounds |
| `EDInternalStatusPanel` | Right-hand internal status panel bounds (two variants) |
| `EDNavigationPanel` | Navigation panel bounds (two variants) |
| `EDGalaxyMap` | Galaxy map panel (auto-calculated from Codex, plus cartographics sub-region) |
| `EDSystemMap` | System map panel (auto-calculated from Codex, plus cartographics sub-region) |
| `EDStationServicesInShip` | Station services, commodities market, and commodity sub-regions |

## Dependencies

| Module | Purpose |
|---|---|
| `cv2` (opencv-python) | Image filtering, color space conversion, thresholding, CLAHE |
| `numpy` | Array operations for HSV ranges, pixel counting |
| `json` | Loading/saving region configs and calibration data |
| `os` | File existence checks for config paths |
| `copy` | `copy()` used in `Quad.get_top_left()` / `get_bottom_right()` |
| `typing.TypedDict` | Type definitions for calibration data structures |

## Notes

- Region rects are stored as `[left, top, right, bottom]` in fractional screen coordinates (0.0-1.0), loaded from resolution-specific JSON files under `configs/screen_regions/res_{W}_{H}/`.
- Ship-specific region configs are tried first (`{ship_type}.json`), falling back to `default.json`.
- The `inv_col` parameter on capture methods controls RGB/BGR conversion -- see `CLAUDE.md` rule: always use `inv_col=False` for correct BGR from mss.
- `filter_bright()` exists but is unused (not mapped in `_REGION_FILTERS`).
- `blue_color_range` is defined but not mapped to any region in `_REGION_FILTERS`.
