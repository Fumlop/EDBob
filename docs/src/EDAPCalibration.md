# EDAPCalibration.py

## Purpose
Manages OCR calibration for Elite Dangerous cockpit regions. Provides UI controls for calibrating screen regions and sub-regions, and handles compass and target calibration operations.

## Key Classes/Functions
- `Calibration`: Main class managing OCR calibration UI and data
- `str_to_float(input_str)`: Safely converts string to float with default fallback

## Key Methods
- `create_calibration_tab(tab)`: Creates the calibration UI with region/sub-region editors
- `save_ocr_calibration_data()`: Persists calibration changes to ocr_calibration.json
- `reset_all_calibrations()`: Resets all calibrations to defaults
- `on_region_select(event)`: Handles region dropdown selection and displays overlays
- `on_subregion_select(event)`: Handles sub-region selection within a region
- `on_region_size_change()`: Updates region boundaries in real-time
- `on_subregion_size_change()`: Updates sub-region boundaries in real-time
- `calibrate_compass_callback()`: Triggers compass calibration
- `calibrate_callback()`: Triggers target calibration
- `calibrate_region_help()`: Opens online calibration documentation

## Dependencies
- tkinter (ttk)
- Screen_Regions (Quad, scale_region, load_ocr_calibration_data, MyRegion)
- json
- os

## Notes
- Calibration data stored as normalized rectangles [left, top, right, bottom] with values 0.0-1.0
- Sub-regions are scaled relative to their parent regions
- All UI updates trigger overlay visualization for real-time feedback
- Regions are filtered to exclude compass, target, and subregion entries in main dropdown
