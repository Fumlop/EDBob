# EDInternalStatusPanel.py -- Internal (Right) Status Panel

## Purpose

Handles the right-hand ship status panel: panel open/close, tab detection, inventory navigation, and Fleet Carrier cargo transfers. Uses perspective transform to deskew the angled panel for accurate OCR.
Lives in `src/ed/EDInternalStatusPanel.py`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `dummy_cb(msg, body=None)` | None | No-op callback for standalone testing |

## Class: EDInternalStatusPanel

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `screen` | Screen | Screen capture instance |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Parent reference |
| `ocr` | OCR | OCR instance from ed_ap |
| `screen` | Screen | Screen capture |
| `keys` | EDKeys | Key sender |
| `ap_ckb` | callable | GUI callback |
| `locale` | dict | Localized tab name strings |
| `status_parser` | StatusParser | Status.json reader |
| `reg` | dict | Screen regions: `panel_bounds1`, `panel_bounds2` (loaded from calibration) |
| `sub_reg` | dict | Sub-regions within panel: `tab_bar`, `H`, `sts_pnl_tab` |
| `panel_quad_pct` | Quad | Panel quadrilateral in percent coordinates |
| `panel_quad_pix` | Quad | Panel quadrilateral in pixel coordinates |
| `_transform` | ndarray | Forward perspective warp transform |
| `_rev_transform` | ndarray | Reverse perspective warp transform |

### Locale Tab Names

| Key | Description |
|---|---|
| `INT_PNL_TAB_MODULES` | "MODULES" tab text |
| `INT_PNL_TAB_FIRE_GROUPS` | "FIRE GROUPS" tab text |
| `INT_PNL_TAB_SHIP` | "SHIP" tab text |
| `INT_PNL_TAB_INVENTORY` | "INVENTORY" tab text |
| `INT_PNL_TAB_STORAGE` | "STORAGE" tab text |
| `INT_PNL_TAB_STATUS` | "STATUS" tab text |

### Methods

| Method | Returns | Description |
|---|---|---|
| `customize_regions()` | None | Produces pixel-space quadrilateral from two bounds rectangles using `rects_to_quadrilateral()`. |
| `capture_panel_straightened()` | image or None | Grab panel image, deskew via `image_perspective_transform()`. Stores transforms. Shows debug overlay if enabled. |
| `capture_tab_bar()` | image or None | Capture straightened panel, crop to `tab_bar` sub-region. Shows debug overlay if enabled. |
| `capture_inventory_panel()` | image or None | Capture straightened panel, crop to `inventory_panel` sub-region. |
| `show_panel()` | (bool, str) | Opens internal panel if not already open. Returns (active, tab_name). Uses `UIFocus` + `UI_Right` key sequence. |
| `hide_panel()` | None | Closes internal panel via `goto_cockpit_view()` if `GuiFocusInternalPanel` is active. |
| `is_panel_active()` | (bool, str) | Detects if panel is open and which tab is active using `ocr.detect_highlighted_tab_index()`. Retries up to 10 times with `CycleNextPanel`. |
| `show_inventory_tab()` | bool or None | Navigates to INVENTORY tab from any current tab using `CycleNextPanel` with appropriate repeat count. |
| `transfer_to_fleetcarrier(ap)` | None | Transfer all goods to Fleet Carrier via inventory panel UI sequence. |
| `transfer_from_fleetcarrier(ap, buy_commodities)` | None | Transfer specific commodity from Fleet Carrier to ship. Uses `buy_commodities['Down']` for item index. |

### Tab Navigation (from detected tab to INVENTORY)

| Current Tab | CycleNextPanel Repeats |
|---|---|
| MODULES | 3 |
| FIRE GROUPS | 2 |
| SHIP | 1 |
| INVENTORY | 0 (already there) |
| STORAGE | 7 (wrap around) |
| STATUS | 6 (wrap around) |

## Dependencies

| Module | Purpose |
|---|---|
| `EDNavigationPanel` | `rects_to_quadrilateral`, `image_perspective_transform`, `image_reverse_perspective_transform` |
| `Screen` | `crop_image_by_pct` |
| `Screen_Regions` | `Quad`, `load_calibrated_regions` |
| `StatusParser` | GUI focus detection (`GuiFocusInternalPanel`) |
| `EDAP_data` | `GuiFocusInternalPanel` constant |
| `cv2` | Image writing for debug output |

## Notes

- Panel is perspective-skewed in game; deskewing is required for accurate OCR/detection
- Tab detection uses pixel color (highlighted tab index), not OCR on text
- Debug images written to `test/status-panel/out/` directory
- Fleet Carrier transfers assume specific menu layout and cursor positions
