# Overlay.py -- Win32 Debug Overlay

## Purpose

Transparent overlay window for drawing rectangles, quadrilaterals, and text on top of the Elite Dangerous game window. Uses Win32 API with a layered, topmost, click-through window.
Lives in `src/screen/Overlay.py`.

## Module-Level Globals

| Global | Type | Description |
|---|---|---|
| `lines` | dict | Rectangle overlays keyed by string ID |
| `text` | dict | Grid-positioned text overlays keyed by string ID |
| `floating_text` | dict | Absolute-positioned text overlays keyed by string ID |
| `quadrilaterals` | dict | Quadrilateral overlays keyed by string ID |
| `fnt` | list | Font settings `[name, size, computed_height]` |
| `pos` | list | Text grid origin `[x, y]` |
| `elite_dangerous_window` | str | `"Elite - Dangerous (CLIENT)"` |

## Class: Vector

Simple rectangle/position holder.

| Method | Description |
|---|---|
| `__init__(x, y, w, h)` | Store position and dimensions |
| `__ne__(other)` | Compare by sum of components |

## Class: Overlay

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `parent_window` | str | Window title to track and overlay. Empty string for no tracking. |
| `elite` | int | If 1, override parent with `elite_dangerous_window` constant. |

### Constructor Behavior

1. Starts `overlay_win32_run` on daemon thread (creates Win32 window)
2. Starts `_overlay_cleanup_loop` on daemon thread (removes expired overlays)
3. If parent specified, finds window handle and positions overlay to match

### Win32 Window Properties

- Extended styles: `WS_EX_COMPOSITED | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TRANSPARENT`
- Styles: `WS_DISABLED | WS_POPUP | WS_VISIBLE`
- Color key: white (`0x00ffffff`) is transparent
- Full screen size, repositioned to parent window bounds

### Methods -- Adding Overlays

| Method | Description |
|---|---|
| `overlay_rect(key, pt1, pt2, color, thick, duration=3.0)` | Add rectangle by two corner tuples. Duration < 0 = permanent. |
| `overlay_rect1(key, rect, color, thick, duration=3.0)` | Add rectangle by `[x1, y1, x2, y2]` list. |
| `overlay_quad_pct(key, quad, color, thick, duration=3.0)` | Add quadrilateral in percent coords (0.0-1.0), scaled to parent window. |
| `overlay_quad_pix(key, quad, color, thick, duration=3.0)` | Static. Add quadrilateral in pixel coords. |
| `overlay_text(key, txt, row, col, color, duration=3.0)` | Add text at grid position (row, col). |
| `overlay_floating_text(key, txt, x, y, color, duration=3.0)` | Add text at absolute pixel position. |

### Methods -- Configuration

| Method | Description |
|---|---|
| `overlay_setfont(fontname, fsize)` | Set font name and size for text rendering. |
| `overlay_set_pos(x, y)` | Set text grid origin in pixels. |

### Methods -- Removing Overlays

| Method | Description |
|---|---|
| `overlay_clear()` | Remove all overlays (lines, quads, text, floating_text). No redraw. |
| `overlay_remove_rect(key)` | Remove specific rectangle. No redraw. |
| `overlay_remove_quad(key)` | Remove specific quadrilateral. No redraw. |
| `overlay_remove_text(key)` | Remove specific text. No redraw. |
| `overlay_remove_floating_text(key)` | Remove specific floating text. No redraw. |

### Methods -- Rendering

| Method | Description |
|---|---|
| `overlay_paint()` | Force redraw. Repositions to parent window if it moved. |
| `overlay_quit()` | Post WM_CLOSE to destroy overlay window. |
| `shutdown()` | Post WM_DESTROY and join overlay thread (3s timeout). |

### Methods -- Internal

| Method | Description |
|---|---|
| `overlay_win32_run()` | Thread target: creates Win32 window, enters message pump. |
| `_GetTargetWindowRect()` | Get current parent window rect. Returns last known on failure. |
| `_overlay_cleanup_loop()` | Thread target: polls every 0.5s, removes expired overlays, triggers redraw. |

### Static Drawing Methods

| Method | Description |
|---|---|
| `overlay_draw_rect(hdc, pt1, pt2, line_type, color, thick)` | Draw decorative rectangle with corner brackets and center tics. Small rects (< 20px) drawn as simple outline. |
| `overlay_draw_quad(hdc, quad, line_type, color, thick)` | Draw quadrilateral outline from Quad object. |
| `overlay_set_font(hdc, fontname, fontSize)` | Create and select Win32 font with DPI scaling. Uses `NONANTIALIASED_QUALITY` to avoid white edges. |
| `overlay_draw_text(hWnd, hdc, txt, row, col, color)` | Draw text at grid position using current font and origin. |
| `overlay_draw_floating_text(hWnd, hdc, txt, x, y, color)` | Draw text at absolute pixel position. |
| `wndProc(hWnd, message, wParam, lParam)` | Static Win32 window procedure handling `WM_PAINT` and `WM_DESTROY`. |

## Dependencies

| Module | Purpose |
|---|---|
| `win32api` / `win32con` / `win32gui` / `win32ui` | Win32 API for window creation and drawing |
| `Screen_Regions` | `Quad`, `Point` geometry classes |

## Notes

- All overlay add methods do NOT force a redraw; call `overlay_paint()` after adding
- Duration parameter: positive = auto-expire after N seconds, negative = permanent until removed
- White color (`0x00ffffff`) is the transparency key -- do not use white for drawing
- Parent window tracking: overlay repositions itself when parent window moves
- Global dicts are shared across instances (module-level state)
- Thread-safe drawing via Win32 message loop on separate daemon thread
