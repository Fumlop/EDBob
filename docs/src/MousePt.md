# MousePt.py -- Mouse Input Handler

## Purpose

Mouse click detection and simulation using `pynput`. Provides blocking click-location capture and programmatic click at coordinates.
Lives in `src/core/MousePt.py`.

## Class: MousePoint

### Constructor

No parameters. Initializes position to (0, 0), creates pynput `Controller`.

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `x` | int | Last captured X coordinate |
| `y` | int | Last captured Y coordinate |
| `term` | bool | Termination flag for listener loop |
| `ls` | Listener or None | pynput mouse listener (created on demand) |
| `ms` | Controller | pynput mouse controller |

### Methods

| Method | Returns | Description |
|---|---|---|
| `on_move(x, y)` | True | Mouse move callback (no-op, keeps listener alive). |
| `on_scroll(x, y, dx, dy)` | True | Mouse scroll callback (no-op, keeps listener alive). |
| `on_click(x, y, button, pressed)` | True | Mouse click callback. Stores coordinates and sets `term = True`. |
| `get_location()` | (x, y) | Blocking: starts mouse listener, waits for click, returns click coordinates. Stops listener after capture. |
| `do_click(x, y, delay=0.1)` | None | Move mouse to (x, y), press left button, wait `delay` seconds, release. |

## Module-Level Functions

| Function | Description |
|---|---|
| `main()` | Test harness: calls `do_click(1977, 510)`. |

## Dependencies

| Module | Purpose |
|---|---|
| `pynput.mouse` | Mouse listener (`Listener`) and controller (`Controller`) |

## Notes

- `get_location()` creates a new listener each call (not reusable)
- `do_click()` uses press/release with configurable delay (default 0.1s)
- Handles `KeyboardInterrupt` gracefully in `get_location()`
- Used for calibration and manual coordinate capture
