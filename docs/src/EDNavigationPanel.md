# EDNavigationPanel.py

## Purpose
Navigation (left-hand) panel: target row detection for SC Assist activation and docking requests. Menu key sequences are delegated to MenuNav. Also exports perspective transform utilities shared with EDInternalStatusPanel.

## Module-level Functions (shared utilities)
- **image_perspective_transform(image, src_quad)**: Deskews a panel image via perspective warp. Returns (image, transform, reverse_transform).
- **image_reverse_perspective_transform(image, src_quad, rev_transform)**: Reverse-warps coordinates back to skewed panel space for overlay drawing.
- **rects_to_quadrilateral(rect_tlbr, rect_bltr)**: Converts two bounding rectangles into a quadrilateral shape.

## Class: EDNavigationPanel

### Target Row Detection
- **_load_templates()**: Class method, loads and caches bracket templates (`bracket_lt.png` flipped/inverted)
- **_is_target_row_selected(seen_bracket)**: Combined detection using orange mask bracket absence + inverted grayscale bracket presence. Passed as callback to `MenuNav.activate_sc_assist()`

### Detection Constants
- `NAV_LIST_BOX`: (264, 400, 1200, 800) -- crop region for nav list rows
- `ORANGE_BRACKET_HIGH`: 0.70 -- bracket clearly visible (not on target)
- `ORANGE_BRACKET_LOW`: 0.60 -- bracket gone (target found)
- `INV_BRACKET_THRESHOLD`: 0.65 -- inverted bracket match confirms target

### MenuNav Delegates
- **activate_sc_assist()** -> `MenuNav.activate_sc_assist()` with `_is_target_row_selected` callback
- **request_docking()** -> `MenuNav.request_docking()`
- **hide_panel()** -> `MenuNav.goto_cockpit()` when panel is open
- **lock_destination()** -> Deprecated stub, returns False

## Dependencies
- MenuNav: All menu key sequences delegated here
- cv2/numpy: Template matching, color conversion
- StatusParser: GUI focus state detection

## Removed (consolidated into MenuNav or unused)
- All perspective transform capture methods (capture_panel_straightened, capture_tab_bar, capture_location_panel)
- OCR-based tab detection (show_panel, is_panel_active, show_navigation_tab, show_contacts_tab)
- Panel region config (reg, sub_reg, panel_quad_pct/pix, transforms)
- Locale tab text strings
