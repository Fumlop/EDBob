# Screen.py -- Screen Capture and Monitor Detection

## Purpose

Handles screen captures from the Elite Dangerous window, detects which monitor ED is running on, manages resolution scaling, and provides methods to grab and crop screen regions for image analysis. Lives in `src/screen/Screen.py`.

## Architecture

- Module-level constant `elite_dangerous_window` = `"Elite - Dangerous (CLIENT)"` used throughout for window lookup
- `Screen` class wraps `mss` for multi-monitor screenshot capture
- Supports two modes: live screen capture (`using_screen=True`) or static image injection for testing (`using_screen=False`)
- Resolution scaling loaded from `configs/resolution.json`, falls back to hardcoded table, then to dynamic calculation relative to 3440x1440

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `set_focus_elite_window()` | None | Set focus to the ED window. Uses Win32 `AttachThreadInput` trick to bypass `SetForegroundWindow` restrictions. No-op if ED already has focus. |
| `crop_image_by_pct(image, quad)` | image | Crop an image using percentage-based coordinates (0.0-1.0). Makes a copy of the Quad, scales to pixels, delegates to `crop_image_pix`. |
| `crop_image_pix(image, quad)` | image | Crop an image using pixel-based coordinates [L, T, R, B]. Direct numpy slice `image[y:y+h, x:x+w]`. |

## Screen Class

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap_ckb` | callable | Callback for GUI logging |
| `mss` | mss.mss | MSS screenshot instance |
| `using_screen` | bool | True = live capture, False = static image mode |
| `_screen_image` | ndarray or None | Injected image for testing mode |
| `screen_width` | int | ED client area width in pixels |
| `screen_height` | int | ED client area height in pixels |
| `screen_left` | int | ED client area left offset in screen coords |
| `screen_top` | int | ED client area top offset in screen coords |
| `monitor_number` | int | MSS monitor index (1-based) |
| `aspect_ratio` | float | `screen_width / screen_height` |
| `mon` | dict or None | MSS monitor dict for the active monitor |
| `scales` | dict | Resolution-to-scale mapping, keyed by `"WxH"` string |
| `scaleX` | float | Horizontal scale factor for current resolution |
| `scaleY` | float | Vertical scale factor for current resolution |

### Methods

| Method | Returns | Description |
|---|---|---|
| `__init__(cb)` | None | Init MSS, find ED window via `get_elite_window_rect`, match to monitor, use `get_elite_client_rect` for game area dimensions (handles windowed borderless with taskbar). Load `resolution.json` scaling config. |
| `get_elite_window_rect()` | `(L, T, R, B)` or None | Static. Find ED window handle via `win32gui.FindWindow`, return full window rect. |
| `get_elite_client_rect()` | `(L, T, R, B)` or None | Static. Find ED window handle, get client area via `GetClientRect`, convert to screen coordinates via `ClientToScreen`. Excludes title bar and borders. |
| `elite_window_exists()` | bool | Static. Check if ED client window handle exists. |
| `write_config(data, fileName)` | None | Write scale dict to JSON file. Default path: `./configs/resolution.json`. |
| `read_config(fileName)` | dict or None | Read scale dict from JSON file. Default path: `./configs/resolution.json`. Returns None on error. |
| `get_screen_region(reg, rgb)` | image | Capture screen region from pixel coordinates `[x_left, y_top, x_right, y_bot]`. Delegates to `get_screen`. |
| `get_screen(x_left, y_top, x_right, y_bot, rgb)` | image | Core capture method. Offsets coords by `screen_left`/`screen_top`, grabs via MSS. If `rgb=True` applies `COLOR_RGB2BGR` conversion (note: this is a known bug -- MSS returns BGRA, so this swap corrupts channel order). |
| `get_screen_rect_pct(rect)` | image or None | Capture region defined by percentage rect `[L, T, R, B]` (0.0-1.0). In live mode: converts to abs, calls `get_screen`, then undoes the `COLOR_RGB2BGR` with a `COLOR_BGR2RGB`. In static image mode: crops from `_screen_image` using `crop_image_by_pct`. |
| `screen_rect_to_abs(rect)` | list | Convert percentage rect to pixel rect by multiplying by `screen_width`/`screen_height`. |
| `screen_region_pct_to_pix(quad)` | Quad | Convert a Quad from percentage coords to pixel coords. Returns a copy. |
| `get_screen_full()` | image or None | Capture entire ED window. In live mode: calls `get_screen` for full area, undoes `COLOR_RGB2BGR`. In static mode: returns `_screen_image`. |
| `set_screen_image(image)` | None | Inject a static image for testing. Sets `using_screen=False`, updates `screen_width`/`screen_height` from image shape, resets `screen_left`/`screen_top` to 0. |

## Built-in Scale Table

Default scale factors (overridden by `configs/resolution.json`):

| Resolution | scaleX | scaleY | Status |
|---|---|---|---|
| 1024x768 | 0.39 | 0.39 | Tested (lower match %) |
| 1080x1080 | 0.5 | 0.5 | Not tested |
| 1280x800 | 0.48 | 0.48 | Tested |
| 1280x1024 | 0.5 | 0.5 | Tested |
| 1600x900 | 0.6 | 0.6 | Tested |
| 1920x1080 | 0.75 | 0.75 | Tested |
| 1920x1200 | 0.73 | 0.73 | Tested |
| 1920x1440 | 0.8 | 0.8 | Tested |
| 2560x1080 | 0.75 | 0.75 | Tested |
| 2560x1440 | 1.0 | 1.0 | Tested |
| 3440x1440 | 1.0 | 1.0 | Tested |

If resolution not found in table, scales are calculated as `screen_width / 3440.0` and `screen_height / 1440.0`.

## Dependencies

| Module | Purpose |
|---|---|
| `cv2` (OpenCV) | Color space conversion (`cvtColor`) |
| `win32gui` / `win32con` | Window handle lookup, focus management |
| `ctypes` | Thread input attachment for focus, `ClientToScreen` for client rect |
| `mss` | Multi-monitor screenshot capture |
| `numpy` | Array conversion for captured images |
| `json` | Resolution config file I/O |
| `EDlogger` | Logging |
| `Screen_Regions.Quad` | Rectangle abstraction for percentage/pixel coords |

## Notes

- MSS `grab` returns BGRA. The `get_screen(rgb=True)` path applies `COLOR_RGB2BGR` which corrupts channel order. `get_screen_rect_pct` and `get_screen_full` undo this with a second `COLOR_BGR2RGB` call. All `capture_region` calls should use `inv_col=False` per project rules.
- Monitor detection iterates all MSS monitors (skipping index 0 which is the combined desktop). Matches by comparing monitor `left`/`top` with ED window `left`/`top`.
- Client rect detection via `GetClientRect` + `ClientToScreen` handles windowed borderless mode where a taskbar reduces the game area.
- Falls back to monitor 1 if ED window cannot be matched to any specific monitor.
