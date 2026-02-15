# Overlay.py

## Purpose
Creates transparent Windows overlay for drawing rectangles, text, and quadrilaterals over the Elite Dangerous window. Provides real-time visual debugging and UI feedback capabilities.

## Key Classes/Functions

### Vector
- Internal class representing window boundaries (x, y, width, height)

### Overlay
- Main class for overlay window management and drawing

## Key Methods

- `__init__(parent_window, elite)`: Initialize overlay window (elite=1 for ED window)
- `overlay_rect(key, pt1, pt2, color, thick, duration)`: Add rectangle overlay
- `overlay_rect1(key, rect, color, thick, duration)`: Add rectangle from rect tuple
- `overlay_quad_pct(key, quad, color, thick, duration)`: Add quadrilateral in percentages
- `overlay_quad_pix(key, quad, color, thick, duration)`: Add quadrilateral in pixels (static)
- `overlay_text(key, txt, row, col, color, duration)`: Add text overlay at grid position
- `overlay_floating_text(key, txt, x, y, color, duration)`: Add text at absolute coordinates
- `overlay_setfont(fontname, fsize)`: Set font for text overlays
- `overlay_set_pos(x, y)`: Set base position for grid-based text
- `overlay_paint()`: Force redraw of all overlays
- `overlay_clear()`: Remove all overlays
- `overlay_remove_rect(key)`: Remove specific rectangle
- `overlay_remove_quad(key)`: Remove specific quadrilateral
- `overlay_remove_text(key)`: Remove specific text
- `overlay_remove_floating_text(key)`: Remove specific floating text
- `overlay_quit()`: Close overlay window

## Dependencies

- win32api, win32con, win32gui, win32ui
- threading, datetime
- Screen_Regions (Quad, Point)

## Notes

- Uses Win32 API for transparent, click-through overlay window
- Default duration: 3.0 seconds; negative duration = persistent
- Thread-safe cleanup loop removes expired overlays every 0.5 seconds
- Overlay window styled as WS_EX_TRANSPARENT (click-through) and WS_EX_TOPMOST
- Global dictionaries: lines, text, floating_text, quadrilaterals
- Rectangle drawing distinguishes small (<20px) and large rectangles with tics
- Quad scaling from origin to support percentage-based positioning
- Font rendering uses device-independent scaling (DPI-aware)
- Color format: (R, G, B) tuples with 0-255 values
- Window follows parent window movements via timer
