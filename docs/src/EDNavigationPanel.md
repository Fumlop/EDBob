# EDNavigationPanel.py

## Purpose
Handles the left-hand navigation panel in Elite Dangerous, providing OCR-based detection of tabs, location lists, and destination locking. Includes perspective transform utilities to deskew the panel for accurate text recognition.

## Key Classes/Functions
- **EDNavigationPanel**: Main class managing navigation panel interactions
- **image_perspective_transform()**: Applies perspective warp to remove panel skew
- **image_reverse_perspective_transform()**: Reverse warps coordinates back to skewed panel space
- **rects_to_quadrilateral()**: Converts two rectangles into a quadrilateral shape

## Key Methods
- **capture_panel_straightened()**: Captures and deskews the navigation panel image
- **capture_tab_bar()**: Extracts the tab bar region (NAVIGATION/TRANSACTIONS/CONTACTS/TARGET)
- **capture_location_panel()**: Extracts the location list region
- **show_panel()**: Opens the navigation panel if not already visible
- **is_panel_active()**: Detects if panel is open and returns active tab name via OCR
- **show_navigation_tab()**: Navigates to the NAVIGATION tab
- **show_contacts_tab()**: Navigates to the CONTACTS tab
- **lock_destination()**: Finds and locks a destination in the location list
- **request_docking()**: Requests docking from the CONTACTS tab
- **find_destination_in_list()**: Scrolls through location list with OCR matching
- **scroll_to_top_of_list()**: Scrolls to beginning of location list

## Dependencies
- cv2 (OpenCV): Image perspective transforms
- numpy: Array operations
- Screen_Regions: Quad/Point classes and region calibration
- StatusParser: GUI focus state detection
- EDlogger: Logging
- EDAP_data: GUI focus constants
- Screen: Image cropping utilities

## Notes
- Uses perspective transforms to handle the angled/skewed panel display
- All regions calibrated via `load_calibrated_regions()` from external config
- OCR similarity matching (0.8 threshold) for destination name detection
- Handles repetitive list items via y-position cycling detection
- Debug overlay support for visual debugging
