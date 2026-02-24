# src/screen/Screen.py (353 lines)

Low-level screen capture and Elite Dangerous window management.

## Key Functions

| Function | Description |
|----------|-------------|
| `set_focus_elite_window()` | Bring ED window to foreground via win32gui |
| Screen.capture_region() | Grab a region via mss, apply filters |
| Screen.capture_region_filtered() | Grab + HSV color filter |

## Screen Capture

Uses `mss` for fast screen grabs. Returns BGRA -> converted as needed.

**Important**: Always use `inv_col=False`. The `rgb=True` path does a bogus
color swap that breaks orange/cyan detection. See CLAUDE.md rule.

## Window Detection

Finds the ED window by title (`ED_WINDOW_TITLE` from constants) using win32gui.
Falls back to full screen if window not found.

## Dependencies

- `mss` -- screen capture
- `cv2` -- image conversion
- `win32gui` -- window management
- `src.core.constants` -- ED_WINDOW_TITLE
