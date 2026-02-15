# OCR.py

## Purpose
Performs Optical Character Recognition (OCR) on game screenshots using PaddleOCR. Provides text detection, similarity matching, and item highlighting detection with optional debug output.

## Key Classes/Functions

### OCR
- Main class for OCR operations using PaddleOCR library

## Key Methods

- `__init__(ed_ap, screen)`: Initialize OCR engine, string similarity matchers
- `image_ocr(image, name)`: Full OCR with position data
  - Returns: (ocr_data with coordinates, text list) or (None, None)
- `image_simple_ocr(image, name)`: Simplified OCR text-only extraction (faster)
  - Returns: list of detected text strings or None
- `string_similarity(s1, s2)`: Compare strings with normalized Levenshtein distance
  - Returns: float 0.0 (no match) to 1.0 (identical)
- `get_highlighted_item_data(image, item)`: Extract text from selected menu item
  - Uses orange/blue background detection to find highlighted area
- `get_highlighted_item_in_image(image, item)`: Find highlighted item by HSV mask
  - Returns: (cropped image, Quad position in %)
- `is_text_in_image(image, text, name)`: Check if text exists in image
  - Returns: (True/False, detected text string)
- `is_text_in_region(text, region)`: Check if text exists in screen region
- `is_text_in_selected_item_in_image(img, text, item, name)`: Check text in highlighted item
- `select_item_in_list(text, region, keys, quad, name)`: Find and select item in menu by text
- `wait_for_text(ap, texts, region, timeout)`: Block until text appears in region
- `capture_region_pct(region)`: Extract image from screen region (percentage coords)

## Dependencies

- cv2 (OpenCV)
- PaddleOCR
- numpy
- strsimpy (string similarity)
- EDlogger
- Screen_Regions (Quad, Point)

## Notes

- PaddleOCR initialization disables doc orientation, unwarping, and textline orientation
- Uses normalized Levenshtein distance for string matching (other matchers available: JaroWinkler, SorensenDice)
- Highlighted item detection: HSV color range mask + threshold + morphological opening
- Debug mode saves OCR output to ./ocr_output/ folder (images and JSON)
- Text matching strips spaces and converts to uppercase for comparison
- Contour detection kernel size: 10% of smallest image dimension
- Region coordinates in percentage (0.0-1.0) for resolution independence
