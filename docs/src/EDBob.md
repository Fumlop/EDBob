# src/gui/EDBob.py (817 lines)

Main GUI application. Tkinter-based control panel for the autopilot.

## Class: APGui

Entry point: `python -m src.gui.EDBob`

Creates a single `EDAutopilot` instance at startup. Provides:
- Checkboxes to enable/disable assists (SC, Waypoint, DSS)
- Calibration buttons (Normal, Supercruise)
- Waypoint file loader
- Status display (log messages from autopilot)
- Hotkeys: Home=FSD Assist, Insert=SC Assist, End=Stop All

### Threading

GUI runs on the main thread (tkinter requirement). Autopilot engine runs
on a separate thread. Callbacks update GUI via tkinter's `after()` for
thread safety.

### Ship Property Display

Reads ship properties via `EDAutopilot` proxy properties (e.g. `ap.pitchrate`)
which delegate to `Ship` attributes.

## Dependencies

- `src.autopilot.ED_AP` -- EDAutopilot
- `tkinter`, `sv_ttk` -- GUI framework
