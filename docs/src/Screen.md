# Screen.py

## Purpose
Handles screen captures from the Elite Dangerous window, detects monitor configuration, manages resolution scaling, and provides methods to grab and crop screen regions for image analysis.

## Key Classes/Functions
- **Screen**: Main class for screen capture and region extraction functionality
- **set_focus_elite_window()**: Sets focus to the Elite Dangerous window
- **crop_image_by_pct()**: Crops image using percentage-based coordinates
- **crop_image_pix()**: Crops image using pixel-based coordinates

## Key Methods

### Screen Class

- **__init__(cb)**: Initializes screen capture, detects ED window position, identifies monitor, loads resolution scaling configuration
- **get_elite_window_rect()**: Static method that returns ED window position as (left, top, right, bottom) tuple or None
- **elite_window_exists()**: Static method that checks if ED client is running
- **write_config(data, fileName)**: Saves scaling configuration to JSON file
- **read_config(fileName)**: Loads scaling configuration from JSON file
- **get_screen_region(reg, rgb)**: Captures screen region from percentage-based coordinates
- **get_screen(x_left, y_top, x_right, y_bot, rgb)**: Captures screen region from pixel-based coordinates
- **get_screen_rect_pct(rect)**: Grabs screenshot of region defined by percentage values [L, T, R, B]
- **screen_rect_to_abs(rect)**: Converts percentage coordinates to absolute pixel coordinates
- **screen_region_pct_to_pix(quad)**: Converts Quad object from percentage to pixel coordinates
- **get_screen_full()**: Captures entire ED window as image
- **set_screen_image(image)**: Switches from live screen capture to static image for testing

## Dependencies
- opencv-python (cv2)
- win32con, win32gui (Windows window management)
- mss (multi-screen screenshot)
- numpy
- json
- EDlogger
- Screen_Regions (Quad class)

## Notes
- Automatically detects which monitor ED is running on and adjusts screen capture accordingly
- Supports multiple resolution scaling factors via configuration file at configs/resolution.json
- Includes built-in scale factors for common resolutions (1024x768 through 3440x1440)
- If resolution not in configuration, calculates scale dynamically relative to 3440x1440 base resolution
- Can switch between live screen capture mode and static image mode for testing
- Expects ED window title: "Elite - Dangerous (CLIENT)"
