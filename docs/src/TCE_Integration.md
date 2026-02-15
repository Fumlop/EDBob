# TCE_Integration.py

## Purpose
Integrates with Trade Computer Extension (TCE), a third-party Elite Dangerous overlay tool. Handles shopping list export to TCE format and imports TCE destination data.

## Key Classes/Functions
- `TceIntegration`: Manages all TCE integration operations

## Key Methods
- `write_shopping_list()`: Exports global shopping list to TCE XML shopping list format
- `create_gui_tab(ap_gui, tab)`: Creates TCE configuration UI
- `load_tce_dest()`: Loads current TCE destination from JSON and populates waypoint fields
- `read_resources_db(filepath, table_name)`: Reads SQLite resources database
- `fetch_data_as_dict(db_path, query)`: Executes database query and returns results as list of dicts
- `entry_update(event)`: Updates TCE paths when settings changed
- `goto_tce_webpage()`: Opens TCE forum page in browser

## Dependencies
- sqlite3
- json
- tkinter (ttk)
- os
- webbrowser
- EDlogger

## Notes
- TCE paths configured in app config: TCEInstallationPath (e.g., C:\TCE)
- Shopping list written to TCE\SHOP\ED_AP Shopping List.tsl in XML format
- Destination file loaded from TCE\DUMP\Destination.json
- Database resources linked by commodity name (case-insensitive match)
- Each shopping list item includes: ID, name, category, quantity, average price
- Only includes global shopping list commodities with quantities > 0
- Resource database tables: public_Goods containing Tradegood, Category, AvgPrice, ED_ID
