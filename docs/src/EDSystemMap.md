# EDSystemMap.py

## Purpose
Manages the System Map interface for setting local destinations via bookmarks. Supports both Odyssey and Horizons versions, with special handling for Nav Panel bookmarks.

## Key Classes/Functions
- **EDSystemMap**: Main class handling system map operations

## Key Methods
- **set_sys_map_dest_bookmark()**: Sets destination using bookmarks (Favorite, Body, Station, Settlement, Navigation)
- **goto_system_map()**: Opens System Map, waits for load, positions for bookmark navigation

## Key Attributes
- **is_odyssey**: Game version flag (True=Odyssey, False=Horizons)
- **reg**: Screen regions (full_panel, cartographics)

## Dependencies
- StatusParser: GUI focus state detection
- Screen_Regions: Region calibration and Quad geometry
- EDlogger: Logging
- EDAP_data: GUI focus constants (GuiFocusSystemMap)

## Notes
- Handles both system map bookmarks and nav panel bookmarks
- Navigation bookmark type uses nav panel directly instead of system map
- Waits for CARTOGRAPHICS text as load confirmation
- Includes workaround for first bookmark not always being pre-selected
- Supports Odyssey and Horizons UI navigation with appropriate key sequences
- Uses UI navigation keys (UI_Up, UI_Select, UI_Down, etc.)
