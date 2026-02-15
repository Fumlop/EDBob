# StatusParser.py

## Purpose
Parses Elite Dangerous Status.json file to extract and translate game state flags, fuel, cargo, position, and destination information. Provides flag querying and wait-for-state methods.

## Key Classes/Functions

### StatusParser
- Main class for Status.json file monitoring and state translation

## Key Methods

- `__init__(file_path)`: Initialize parser pointing to Status.json (auto-detects on Windows)
- `get_cleaned_data()`: Read Status.json and return cleaned data with essential fields only
- `get_file_modified_time()`: Returns file modification timestamp
- `translate_flags(flags_value)`: Convert Flags integer to dictionary of True flags
- `translate_flags2(flags2_value)`: Convert Flags2 integer to dictionary of True flags
- `transform_pips(pips_list)`: Convert pips array to {system, engine, weapons} dict (halved)
- `adjust_year(timestamp)`: Add 1286 years to timestamp (game year conversion)
- `wait_for_file_change(start_timestamp, timeout)`: Block until Status.json changes
- `wait_for_flag_on(flag, timeout)`: Block until flag becomes true
- `wait_for_flag_off(flag, timeout)`: Block until flag becomes false
- `wait_for_flag2_on(flag, timeout)`: Block until Flags2 bit becomes true
- `wait_for_flag2_off(flag, timeout)`: Block until Flags2 bit becomes false
- `wait_for_gui_focus(gui_focus_flag, timeout)`: Block until GUI focus matches
- `get_flag(flag)`: Get current value of specific flag
- `get_flag2(flag)`: Get current value of specific Flags2 bit
- `get_gui_focus()`: Get current GUI focus value
- `log_flag_diffs()`: Debug method to print flag state changes

## Dependencies

- json, os, datetime, threading, queue
- EDAP_data (flag constants)
- EDlogger, Voice
- WindowsKnownPaths (Windows only)

## Notes

- Cleaned data includes: timestamp, Flags, Flags2, Pips, GuiFocus, Cargo, LegalState, position (Lat/Long/Heading/Altitude), fuel (Main/Reservoir), balance, destination
- File change detection with exponential backoff retry (0.1s initial, 2x multiply)
- Handles both Windows and Linux paths
- Timestamp delta tracks seconds between consecutive updates
- Returns only True flags from bit translations (cleaner output)
- Commented threading/queue code available for async file watching
