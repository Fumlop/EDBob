# EDAPGui.py

## Purpose
Main GUI application for the Elite Dangerous Autopilot. Provides a tkinter-based user interface for controlling various autopilot assists (FSD, Supercruise, Waypoint, Robigo, DSS, AFK Combat) and managing configuration settings.

## Key Classes
- **APGui**: Main GUI class that initializes and manages all GUI elements, callbacks, and user interactions

## Key Methods
- `__init__(root)`: Initializes the GUI application, loads configuration, sets up hotkeys and UI elements
- `callback(msg, body)`: Handles callbacks from the ED Autopilot engine for updating GUI state
- `check_cb(field)`: Processes checkbox state changes and manages assist mode interactions
- `entry_update(event)`: Reads input fields and updates configuration values
- `gui_gen(win)`: Generates all GUI tabs and widgets (Main, Settings, Debug/Test, Calibration, Waypoints, Colonization, TCE)
- `makeform(win, ftype, fields, r, inc, r_from, rto)`: Creates form fields (checkboxes, spinboxes, entries) with tooltips
- `start_fsd()` / `stop_fsd()`: Controls FSD Route Assist
- `start_sc()` / `stop_sc()`: Controls Supercruise Assist
- `start_waypoint()` / `stop_waypoint()`: Controls Waypoint Assist
- `start_robigo()` / `stop_robigo()`: Controls Robigo Assist
- `start_dss()` / `stop_dss()`: Controls DSS Assist
- `save_settings()` / `load_settings()`: Persists/loads user configuration
- `log_msg(msg)`: Appends timestamped messages to the log window (supports buffering before GUI loads)
- `setup_hotkeys()`: Configures global keyboard hotkeys for assists

## GUI Structure
**Layout**: Top buttons > Notebook tabs > Status bar

**Tabs**:
1. **Main**: MODE section (6 assists), SHIP section (rates/factors, calibration buttons), LOG section (scrollable message list)
2. **Settings**: AUTOPILOT, BUTTONS, FUEL, OVERLAY, KEYS, VOICE, ELW SCANNER, AFK Combat settings
3. **Debug/Test**: File Actions, Help Actions, Debug Settings (log levels), Single Waypoint Assist, RPY Test buttons
4. **Calibration**: OCR-based calibration interface (created by Calibration class)
5. **Waypoints**: Waypoint file editor (created by WaypointEditorTab class)
6. **Colonization**: Colonization waypoints editor (created by ColonizeEditorTab class)
7. **TCE**: TCE integration tab (created by external TCE class)

**Key UI Components**: Checkboxes (assist modes, options), Spinboxes (numeric config), Entry fields (hotkeys, text), Radio buttons (debug level, DSS button), Status labels (status line, jump count)

## Dependencies
- **tkinter** (tk, ttk, filedialog): GUI framework
- **sv_ttk**: Custom themed tkinter widgets
- **pywinstyles**: Windows-specific window styling
- **tktooltip**: Tooltip support
- **keyboard**: Global hotkey capture
- **webbrowser**: Open URLs
- **subprocess**: Check for updates via git
- **EDAPCalibration.Calibration**: Screen calibration tab
- **EDAPColonizeEditor.ColonizeEditorTab**: Colonization editor
- **EDAPWaypointEditor.WaypointEditorTab**: Waypoint editor
- **ED_AP.EDAutopilot**: Core autopilot engine
- **EDlogger.logger**: Logging utility

## Notes
- **God-class issue**: APGui is a large monolithic class (1295 lines) managing UI generation, callbacks, settings, hotkeys, and multiple assist modes. Consider refactoring into smaller, focused classes.
- **Callback system**: Uses string-based message passing (callback method) for communication with ED_AP engine. Better suited to event-based or signal systems.
- **Assist mutual exclusion**: Check_cb enforces that only one primary assist (FSD/SC/Waypoint/Robigo/DSS) runs at a time by disabling UI controls.
- **Log buffering**: Messages logged before GUI loads are queued to handle initialization timing issues.
- **Version checking**: Uses git commands instead of API calls to check for updates (commented-out requests code).
- **Hard-coded constants**: FORM_TYPE_* and EDAP_VERSION are defined as module-level constants.
