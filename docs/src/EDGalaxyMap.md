# EDGalaxyMap.py

## Purpose
Manages the Galaxy Map interface for setting navigation destinations via text input, bookmarks, or system selection. Supports both Odyssey and Horizons game versions.

## Key Classes/Functions
- **EDGalaxyMap**: Main class handling galaxy map operations

## Key Methods
- **set_gal_map_dest_bookmark()**: Sets destination using bookmarks (Favorite, System, Body, Station, Settlement)
- **set_gal_map_destination_text()**: Delegates to version-specific implementation (Odyssey/Horizons)
- **set_gal_map_destination_text_horizons()**: Types destination name and searches (Horizons version)
- **set_gal_map_destination_text_odyssey()**: Navigates search UI and validates nav route updates (Odyssey version)
- **set_next_system()**: Sets next system in jump route
- **goto_galaxy_map()**: Opens Galaxy Map, waits for load, positions at search bar

## Key Attributes
- **is_odyssey**: Game version flag (True=Odyssey, False=Horizons)
- **SystemSelectDelay**: Configurable delay for system selection (0.5 seconds default)
- **reg**: Screen regions (full_panel, cartographics)

## Dependencies
- StatusParser: GUI focus state detection
- Screen_Regions: Region calibration and Quad geometry
- pyautogui: Text input via typewrite()
- EDlogger: Logging
- EDAP_data: GUI focus constants (GuiFocusGalaxyMap)

## Notes
- Handles game-specific UI differences between Odyssey and Horizons
- Validates nav route changes to confirm correct destination selected
- Waits for CARTOGRAPHICS text appearance as load confirmation
- Retries system selection if nav route updates incorrectly
- Uses UI navigation keys (UI_Up, UI_Select, UI_Right, etc.)
