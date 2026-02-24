# src/ed/EDNavigationPanel.py (164 lines)

Left-hand navigation panel reader. Detects target rows, initiates docking requests.

## Class: EDNavigationPanel

### Key Methods

| Method | Description |
|----------|-------------|
| `is_target_row_visible()` | Check if a target row is highlighted |
| `get_target_row_pixel_position()` | Get pixel coords of target row |

### Perspective Transform Utilities

Exported for use by other panel readers:

```python
image_perspective_transform(image, quad)
image_reverse_perspective_transform(image, quad)
```

These deskew the trapezoidal in-game panels into rectangular images for OCR.

## Dependencies

- `src.screen.Screen` -- capture
- `cv2` -- image processing
- `src.ed.MenuNav` -- menu navigation
- `src.ed.StatusParser` -- state verification
