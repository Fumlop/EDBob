# EDAPWaypointEditor.py

## Purpose
Provides a comprehensive waypoint editor UI for managing trading routes. Supports creating, editing, and organizing waypoints with commodity buy/sell lists, fleet carrier operations, and Inara/Spansh CSV imports.

## Key Classes/Functions
- `WaypointEditorTab`: Main editor tab managing waypoints and shopping lists
- `InternalWaypoint`: Data model for individual waypoint with commodities and bookmarks
- `InternalWaypoints`: Container for multiple waypoints
- `ShoppingItem`: Data model for commodity name and quantity
- `SearchableCombobox`: Custom searchable dropdown for commodity selection

## Key Methods
- `create_waypoints_tab()`: Builds the complete waypoint editor UI
- `new_file()`: Creates a new empty waypoint file
- `open_file()`: Opens file dialog to load waypoint JSON
- `save_file()`: Persists changes to current waypoint file
- `save_as_file()`: Saves waypoints to a new file
- `import_spansh_csv()`: Imports waypoints from Spansh route planner CSV
- `add_inara_route()`: Parses and imports trade route data from Inara
- `editor_load_waypoint_file(filepath)`: Loads and parses waypoint JSON, starts file watcher
- `start_file_watcher(filepath)`: Monitors file for external changes and reloads
- `add_waypoint()`, `delete_waypoint()`: Manage waypoint list
- `move_waypoint_up()`, `move_waypoint_down()`: Reorder waypoints
- `add_buy_commodity()`, `add_sell_commodity()`: Manage commodity lists
- `update_waypoints_list()`: Refreshes UI tree view
- `plot_waypoint_system()`: Sets galaxy map destination
- `plot_waypoint_station()`: Uses bookmarks to navigate to stations
- `load_const_comm()`: Loads construction site commodities from JSON and fleet carrier data

## Dependencies
- tkinter (ttk, messagebox, filedialog)
- EDAP_data
- EDAPColonizeEditor (CommodityDict, get_resources_required_dict)
- EDAP_EDMesg_Interface
- EDJournal (read_construction)
- FleetCarrierMonitorDataParser
- threading
- csv
- json
- os
- time

## Notes
- Waypoints stored in ./waypoints/ directory as JSON files
- Each waypoint supports buy/sell commodities with quantities
- Galaxy/System bookmark types and numbers enable automatic navigation
- File watcher auto-reloads if external changes detected (useful for shared files)
- Searchable commodity dropdown filters by prefix matching
- Fleet carrier integration loads cargo data to calculate purchase needs
- Inara import parses text format with From/To/Buy/Sell patterns
