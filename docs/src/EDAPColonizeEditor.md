# EDAPColonizeEditor.py

## Purpose
Manages construction site colonization data including resource requirements, fleet carrier inventory tracking, and commodity needs calculation for multiple orbital/planetary construction sites.

## Key Classes/Functions
- `ColonizeEditorTab`: Main editor for construction sites and their resource requirements
- `TkConstructionSite`: Tkinter-bound construction site data model
- `ConstructionSites`: Container for multiple construction sites
- `TkCommodity`: Tkinter-bound commodity with required/provided amounts
- `ResourcesRequired`: TypedDict for required resources
- `CommodityDict`: TypedDict for commodity aggregation across sites
- `get_resources_required_list(const_sites, const_id)`: Retrieves sorted resources for a site
- `get_resources_required_dict(const_sites, const_id)`: Returns resources as name-keyed dictionary
- `write_json_file(data, filepath)`: Persists construction data to JSON
- `read_json_file(filepath)`: Loads construction data from JSON
- `right(aString, howMany)`: String utility to extract rightmost characters

## Key Methods
- `create_waypoints_tab(parent)`: Builds construction editor UI
- `load_const_file()`: Loads construction sites and fleet carrier data
- `load_const_file2()`: Loads construction.json file
- `load_fleetcarrier_file()`: Loads fleet carrier cargo inventory
- `save_const_file()`: Persists construction site modifications
- `populate_tk_construction()`: Converts raw data to Tkinter models
- `populate_commodities()`: Aggregates resources across included sites
- `populate_tk_commodities()`: Converts commodity aggregates to Tkinter models
- `update_ui()`: Refreshes all UI components
- `update_const_site_list()`: Updates construction site tree view
- `update_commodity_tree()`: Refreshes commodity list with needs > 0
- `on_tree_click(event)`: Toggles Include flag for construction sites
- `delete_waypoint()`: Removes construction site from list
- `get_selected_waypoint()`: Returns currently selected construction site

## Dependencies
- tkinter (ttk, messagebox)
- FleetCarrierMonitorDataParser
- EDlogger
- json
- os
- typing

## Notes
- Construction data stored in ./configs/construction.json
- Sites linked by MarketID for identification
- Resources show: required amount, provided amount, need (required - provided), on fleet carrier, to buy (need - fleet carrier)
- Only displays commodities where need > 0
- Supports orbital and planetary construction sites with automatic name extraction
- Progress displayed as percentage for each site
- Include checkbox allows filtering sites from commodity calculations
