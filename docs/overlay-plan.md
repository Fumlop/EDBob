# Overlay Calibration Tool -- Plan

## Goal

Transparent overlay window on top of Elite Dangerous that captures mouse input
to define screen regions (boxes) for detection. Replaces manual Paint testing
with live preview of crop + HSV mask + pixel stats.

## Architecture

```
+---------------------------+
|  ED Game (fullscreen/bw)  |
|                           |
|   +---[overlay]--------+  |
|   | transparent, click- |  |
|   | through until       |  |
|   | calibration mode    |  |
|   +--------------------+  |
+---------------------------+
```

- **Framework:** tkinter (already in stdlib, supports transparent windows via
  `attributes('-transparentcolor')` on Windows)
- **Alternative:** PyQt5 if tkinter transparency is flaky -- heavier but proven
  for game overlays
- **Mode toggle:** hotkey switches between passthrough (normal gameplay) and
  calibration mode (overlay captures mouse)

## Calibration Flow

1. User presses hotkey (e.g. F10) to enter calibration mode
2. Overlay becomes click-sensitive, shows crosshair cursor
3. User clicks two corners to define a rectangle
4. Overlay draws the box outline (green/red)
5. Live panel shows:
   - Raw crop from mss grab (BGR, inv_col=False)
   - HSV mask with current filter settings
   - Pixel stats: H/S/V min/max/mean, match percentage
6. User can adjust HSV sliders to tune the filter
7. User names the region (e.g. "target_arc", "compass_dot")
8. Export to config (JSON dict with x, y, w, h, hsv_low, hsv_high)
9. Hotkey exits calibration mode, overlay goes back to passthrough

## Live Preview Panel

```
+--------------------------------------------------+
| Region: target_arc          [Save] [Cancel]      |
+--------------------------------------------------+
| Raw Crop        | HSV Mask       | Stats          |
| [mss grab]      | [filtered]     | H: 10-25       |
|                  |                | S: 150-255     |
|                  |                | V: 120-255     |
|                  |                | Match: 34.2%   |
+--------------------------------------------------+
| H low [===|====] high                             |
| S low [===|====] high                             |
| V low [===|====] high                             |
+--------------------------------------------------+
```

- Preview updates every ~200ms (5 fps, low CPU)
- Shows both inv_col=False (correct) and inv_col=True (broken) side by side
  so user can verify channel order

## Config Export Format

```json
{
  "target_arc": {
    "x": 920, "y": 480, "w": 80, "h": 60,
    "hsv_low": [10, 150, 120],
    "hsv_high": [25, 255, 255],
    "notes": "orange arc around target reticle"
  }
}
```

## Technical Considerations

- **mss grab is BGRA** -- all processing uses inv_col=False (project rule)
- **Resolution independence:** store regions as ratios (x/screen_w) or absolute
  with a reference resolution, recalculate on startup
- **Multi-monitor:** mss monitor selection must match ED's display
- **Topmost window:** overlay needs `wm_attributes('-topmost', True)` to stay
  above ED in borderless/windowed mode
- **Fullscreen exclusive:** true fullscreen blocks overlays -- require
  borderless windowed (most ED players use this anyway)
- **Performance:** only grab screen in calibration mode, not during gameplay

## Modules

| File | Purpose |
|------|---------|
| `src/overlay/overlay_window.py` | tkinter transparent overlay, mouse capture |
| `src/overlay/region_editor.py` | box drawing, HSV slider panel, live preview |
| `src/overlay/config_export.py` | save/load region configs to JSON |

## Dependencies

- tkinter (stdlib)
- mss (already used)
- cv2 (already used)
- numpy (already used)

No new dependencies required.

## Open Questions

- Hotkey binding: global hotkey (pynput) vs ED keybind? pynput already in deps?
- Should regions be editable after creation (drag corners to resize)?
- Store config per-resolution or auto-scale?
- Integrate into existing EDAPGui main window or standalone tool?
