# EDNavigationPanel.py -- Navigation Panel Interactions

## Purpose

Navigation (left-hand) panel: target row detection for SC Assist activation and docking requests. Menu key sequences are delegated to MenuNav. Also exports perspective transform utilities shared with EDInternalStatusPanel.
Lives in `src/ed/EDNavigationPanel.py`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `image_perspective_transform(image, src_quad)` | (image, transform, reverse_transform) | Deskew a nav/internal panel image via perspective warp using `cv2.getPerspectiveTransform`. |
| `image_reverse_perspective_transform(image, src_quad, rev_transform)` | Quad | Reverse-warp coordinates back to skewed panel space for overlay drawing. |
| `rects_to_quadrilateral(rect_tlbr, rect_bltr)` | Quad | Convert two bounding rectangles (top-left/bottom-right and bottom-left/top-right) into a single quadrilateral. |

## Class: EDNavigationPanel

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `screen` | Screen | Screen capture instance |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback |

### Class Constants

| Constant | Value | Description |
|---|---|---|
| `NAV_LIST_BOX` | (264, 400, 1200, 800) | Nav panel list crop region in 1920x1080 pixels |
| `ORANGE_BRACKET_HIGH` | 0.70 | Bracket clearly visible (not on target row) |
| `ORANGE_BRACKET_LOW` | 0.60 | Bracket gone (target row selected or off-page) |
| `INV_BRACKET_THRESHOLD` | 0.65 | Inverted bracket match confirms target selected |

### Methods

| Method | Returns | Description |
|---|---|---|
| `_load_templates()` | None | Class method. Loads and caches `bracket_lt.png` template, creates flipped/inverted variant for `>` detection. |
| `_is_target_row_selected(seen_bracket)` | bool | Combined detection: (1) orange mask template match for `<` bracket disappearance, (2) inverted grayscale `>` match on bright row. Either trigger = target found. |
| `activate_sc_assist()` | bool | Delegates to `MenuNav.activate_sc_assist()` with `_is_target_row_selected` as callback. |
| `request_docking()` | bool | Delegates to `MenuNav.request_docking()`. |
| `hide_panel()` | None | Closes nav panel via `MenuNav.goto_cockpit()` if `GuiFocusExternalPanel` is active. |
| `lock_destination(dst_name)` | bool | DEPRECATED. OCR-based nav panel reading removed. Always returns False. |

### Target Row Detection Algorithm

1. Capture full screen, crop to `NAV_LIST_BOX`
2. Method 1 (orange mask): Template match `<` bracket on orange HSV mask. High score means bracket visible (not on target). Score drop after seeing bracket = target found.
3. Method 2 (inverted grayscale): Template match dark `>` on bright selected row. High score = positive confirmation.
4. Either method triggering returns True.

## Dependencies

| Module | Purpose |
|---|---|
| `MenuNav` | All menu key sequences delegated here |
| `cv2` / `numpy` | Template matching, color conversion, HSV filtering |
| `StatusParser` | GUI focus state detection (`GuiFocusExternalPanel`) |
| `Screen_Regions` | `Quad`, `Point` geometry classes |

## Notes

- Bracket template loaded from `src/ed/templates/bracket_lt.png`
- `seen_bracket` is a mutable list `[bool]` passed by reference to track state across calls
- Perspective transform utilities are used by `EDInternalStatusPanel` for panel deskewing
