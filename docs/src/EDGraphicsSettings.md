# EDGraphicsSettings.py

## Purpose
Reads and validates Elite Dangerous graphics configuration from DisplaySettings.xml and Settings.xml files. Ensures the game is configured for borderless windowed mode and extracts display properties like resolution, monitor, and FOV.

## Key Classes/Functions
- EDGraphicsSettings: Handles parsing of Elite Dangerous graphics configuration files

## Key Methods
- __init__(): Loads and validates both graphics settings files, ensures borderless mode is set
- read_settings(filename): Static method that reads an XML file and returns parsed dictionary data
- Attributes extracted: fullscreen/fullscreen_str (display mode), screenwidth, screenheight, monitor, fov

## Dependencies
- xmltodict: for XML parsing
- os.environ: Windows environment variables (LOCALAPPDATA)
- EDlogger: for logging

## Notes
- Raises exception if graphics settings files don't exist or borderless mode is not enabled
- Hard requirement: Game must be set to borderless windowed mode, not fullscreen or windowed
- Uses Windows LOCALAPPDATA path for file locations
