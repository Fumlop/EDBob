# src/screen/Screen_Regions.py (388 lines)

Region definitions and color-based filters for UI element detection.

## Class: Screen_Regions

Manages named screen regions with resolution-independent coordinates and
HSV color filter configs. Regions are loaded from a JSON calibration file
or computed from screen resolution.

### Region Filter Map

| Region | Filter | Color Range |
|--------|--------|-------------|
| `compass` | equalize | -- |
| `target` | filter_by_color | orange_2 |
| `sun` | filter_sun | -- |
| `disengage` | filter_by_color | blue_sco |
| `sco` | filter_by_color | blue_sco |
| `sc_assist_ind` | filter_by_color | cyan_sc_assist |
| `mission_dest` | equalize | -- |
| `nav_panel` | equalize | -- |
| `center_text` | filter_by_color | orange |

### HSV Color Ranges

| Range | H | S | V | Detects |
|-------|---|---|---|---------|
| orange | 0-25 | 130-235 | 123-220 | Compass ring, text |
| orange_2 | 16-98 | 165-255 | 220-255 | Target reticle |
| blue_sco | 10-100 | 0-150 | 0-255 | Disengage/SCO indicator |
| cyan_sc_assist | 80-110 | 80-255 | 80-255 | SC assist indicator |

## Class: Point

2D coordinate with named access. Immutable-style.

```python
p = Point(100, 200)
p.x()  # 100
p.to_list()  # [100, 200]
Point.from_xy(100, 200)
Point.from_list([100, 200])
```

## Class: Quad

Quadrilateral defined by 4 Points (top-left, top-right, bottom-left, bottom-right).

```python
q = Quad.from_rect(x, y, w, h)
q.width(), q.height(), q.center()
q.offset(dx, dy)
q.scale(factor)  # scale from center
q.inflate(dx, dy)  # grow/shrink
q.subregion(x_pct, y_pct, w_pct, h_pct)  # fractional sub-area
```

## Dependencies

- `cv2`, `numpy` -- image processing
- `src.screen.Screen` -- capture backend
