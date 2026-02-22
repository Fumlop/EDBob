# OCR.py -- Screen Element Detection

## Purpose

Performs screen element detection using OpenCV color/shape analysis. Despite the filename, PaddleOCR has been removed -- all UI checks now use pixel color detection and contour analysis instead of text recognition. Lives in `src/screen/OCR.py`.

## Architecture

- Single class `OCR` provides color-based UI element detection
- String similarity retained via `NormalizedLevenshtein` for comparing text strings
- Highlighted item detection uses HSV masking, thresholding, and morphological operations to find solid orange/blue rectangles
- Tab detection uses HSV orange filtering and x-position averaging

## OCR Class

### Instance Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Reference to the autopilot engine |
| `screen` | Screen | Screen capture instance |
| `normalized_levenshtein` | NormalizedLevenshtein | String similarity calculator |

### Methods

| Method | Returns | Description |
|---|---|---|
| `__init__(ed_ap, screen)` | None | Store references to autopilot and screen, init Levenshtein matcher. |
| `string_similarity(s1, s2)` | float | Compare two strings using normalized Levenshtein distance. Strips brackets, angle brackets, dashes, em-dashes, and spaces before comparison. Returns 0.0 (no match) to 1.0 (identical). |
| `get_highlighted_item_in_image(image, item)` | `(image, Quad)` or `(None, None)` | Static. Find a selected/highlighted menu item in an image. Detects solid orange/blue rectangles (highlighted items have colored background with dark text). Uses HSV mask, grayscale, OTSU threshold, morphological opening, and contour detection. Returns cropped image and Quad position in percentage of image size, or `(None, None)`. Writes debug images to `test/nav-panel/out/`. |
| `capture_region_pct(region)` | image | Grab unfiltered image from a screen region. Takes a region dict with `'rect'` key containing `[L, T, R, B]` in percent (0.0-1.0). Delegates to `screen.get_screen_rect_pct`. |
| `detect_highlighted_tab_index(tab_bar_image, num_tabs)` | int | Detect which tab is active (highlighted) in a tab bar image. Uses HSV orange filter to find highlighted pixels, computes average x-position, maps to tab index. Returns 0-based index, or -1 if not found. |

## Detection Pipeline (get_highlighted_item_in_image)

```
1. HSV mask: H[0-255], S[100-255], V[180-255]  (orange/blue highlight)
2. Grayscale conversion
3. OTSU threshold to binary
4. Morphological opening (kernel = 10% of smallest dimension)
5. Find external contours
6. Filter contours: width > 85% of expected, height > 85% of expected
7. Return first matching contour as cropped image + Quad position
```

Debug output written to `test/nav-panel/out/`:
- `1-input.png` -- original image
- `2-masked.png` -- HSV-masked image
- `3-gray.png` -- grayscale
- `4-thresh1.png` -- OTSU threshold
- `5-opened.png` -- morphological opening result
- `6-contours.png` -- contours drawn on image
- `7-selected_item.png` -- final cropped highlighted item

## Dependencies

| Module | Purpose |
|---|---|
| `cv2` (OpenCV) | HSV conversion, thresholding, morphology, contour detection |
| `numpy` | Array operations, HSV range arrays, `findNonZero` |
| `strsimpy.NormalizedLevenshtein` | String similarity computation |
| `EDlogger` | Logging |
| `Screen_Regions.Quad` | Rectangle abstraction for percentage/pixel coords |

## Notes

- PaddleOCR has been fully removed. The class name `OCR` is historical.
- `string_similarity` strips common OCR artifacts (brackets, dashes, spaces) before comparison -- retained for any future text comparison needs.
- HSV ranges in `get_highlighted_item_in_image` and `detect_highlighted_tab_index` are identical: `[0, 100, 180]` to `[255, 255, 255]`. This catches both orange and blue highlights used in ED menus.
- `detect_highlighted_tab_index` divides image width evenly by `num_tabs` and maps the average x-position of highlighted pixels to a tab index.
