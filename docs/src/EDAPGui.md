# EDAPGui.py -- Main GUI Application

## Purpose

Main GUI application for the Elite Dangerous Autopilot. Provides a tkinter-based user interface
for controlling waypoint assist, managing configuration settings, loading waypoint files, and
editing commodity quantities. Lives in `src/gui/EDAPGui.py`. Entry point is `APGui` class,
instantiated by `main()`.

## Architecture

- Single class `APGui` owns the root tkinter window and all notebook tabs
- Communicates with `ED_AP.EDAutopilot` via a string-based callback system (`callback()`)
- Log messages are buffered in a `queue.Queue` until the GUI finishes loading
- Hotkeys are managed globally via the `keyboard` library
- Update checking uses `git fetch` + commit hash comparison (no API calls)

## Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `EDAP_VERSION` | `"V1.9.0 b4"` | Current release version string, used for update checks |
| `FORM_TYPE_CHECKBOX` | `0` | Form field type: checkbox |
| `FORM_TYPE_SPINBOX` | `1` | Form field type: spinbox |
| `FORM_TYPE_ENTRY` | `2` | Form field type: text entry |

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `str_to_float(input_str)` | `float` | Safe string-to-float conversion, returns 0.0 on error |
| `apply_theme_to_titlebar(root)` | None | Apply dark/light title bar color on Windows 10/11 via pywinstyles |
| `main()` | None | Create root Tk window, instantiate APGui, set dark theme, run mainloop |

## TypedDicts

| TypedDict | Fields | Description |
|---|---|---|
| `SubRegion` | `rect: list[float]`, `text: str` | Screen sub-region definition |
| `Objects` | `width: float`, `height: float`, `text: str` | Screen object definition |
| `MyRegion` | `rect: list[float]`, `text: str`, `readonly: bool`, `regions: dict`, `objects: dict` | Full screen region with sub-regions and objects |

## APGui Methods

### Initialization and Lifecycle

| Method | Returns | Description |
|---|---|---|
| `__init__(root)` | None | Init GUI: create EDAutopilot instance, MousePoint, build all tabs, load config into fields, setup hotkeys, check updates |
| `quit()` | None | Calls `close_window()` |
| `close_window()` | None | Stop all assists, quit EDAutopilot, destroy root window |
| `restart_program()` | None | Stop assists, quit AP, re-exec the Python process via `os.execv` |

### Callback System

| Method | Returns | Description |
|---|---|---|
| `callback(msg, body)` | None | Central callback from EDAutopilot. Routes by msg string: `log`, `log+vce`, `statusline`, `waypoint_stop`, `waypoint_start`, `stop_all_assists`, `jumpcount`, `update_ship_cfg` |

### Assist Controls

| Method | Returns | Description |
|---|---|---|
| `start_waypoint()` | None | Enable waypoint assist on EDAutopilot, set `WP_A_running` flag |
| `stop_waypoint()` | None | Disable waypoint assist on EDAutopilot, clear flag, set status to Idle |
| `stop_all_assists()` | None | Fire `stop_all_assists` callback to halt all running assists |

### Waypoint and Commodity Management

| Method | Returns | Description |
|---|---|---|
| `load_waypoint_file()` | None | Open file dialog for JSON waypoint file, call `_do_load_waypoint` |
| `load_last_waypoint_file()` | None | Load the previously used waypoint file from config `WaypointFilepath` |
| `_do_load_waypoint(filepath)` | None | Load waypoint file via `ed_ap.waypoint`, update label, refresh commodity tree |
| `refresh_commodity_tree()` | None | Clear and rebuild the commodity Treeview from loaded waypoints (Buy/Sell per waypoint + GlobalShoppingList) |
| `_on_commodity_select(event)` | None | On Treeview row select, populate qty spinbox with current value |
| `update_commodity_qty()` | None | Update selected Treeview row qty from spinbox value |
| `save_commodities()` | None | Rebuild waypoint commodity dicts from Treeview, write to waypoint JSON file |

### Settings Management

| Method | Returns | Description |
|---|---|---|
| `save_settings()` | None | Call `entry_update`, then save config and ship configs to JSON files |
| `load_settings()` | None | Reload ship configs from JSON |
| `entry_update(event)` | None | Read all GUI fields (ship rates, AP settings, fuel, overlay, hotkeys, keys) into `ed_ap` config and attributes, call `process_config_settings()` |
| `update_ship_cfg()` | None | Refresh ship rate fields (PitchRate, YawRate, SunPitchUp+Time, PitchFactor, YawFactor) from `ed_ap` attributes |

### Checkbox and Radio Button Handling

| Method | Returns | Description |
|---|---|---|
| `check_cb(field)` | None | Master checkbox/radio handler. Manages: Waypoint Assist toggle, Enable Randomness, Activate Elite for each key, Automatic logout, Enable Overlay, Enable CV View, DSS Button, debug mode radio, Debug Overlay, Enable Hotkeys, Debug OCR, Debug Images |

### Hotkeys

| Method | Returns | Description |
|---|---|---|
| `setup_hotkeys()` | None | Clear all hotkeys, re-register Stop All and Start FSD hotkeys if `HotkeysEnable` is true |

### Logging and Status

| Method | Returns | Description |
|---|---|---|
| `log_msg(msg)` | None | Timestamped log to GUI Listbox. Buffers in queue before GUI loads, flushes on first post-load call |
| `set_statusbar(txt)` | None | Update status bar label text |
| `update_jumpcount(txt)` | None | Update jump count label text |
| `update_statusline(txt)` | None | Update status label with "Status: " prefix, also log the update |

### Ship Testing

| Method | Returns | Description |
|---|---|---|
| `ship_tst_pitch()` | None | Set `ship_tst_pitch_enabled` flag on EDAutopilot (continuous calibration) |
| `ship_tst_roll()` | None | Set `ship_tst_roll_enabled` flag on EDAutopilot (continuous calibration) |
| `ship_tst_yaw()` | None | Set `ship_tst_yaw_enabled` flag on EDAutopilot (continuous calibration) |
| `ship_tst_pitch_30()` | None | Test pitch by 30 degrees |
| `ship_tst_pitch_45()` | None | Test pitch by 45 degrees |
| `ship_tst_pitch_90()` | None | Test pitch by 90 degrees |
| `ship_tst_roll_30()` | None | Test roll by 30 degrees |
| `ship_tst_roll_45()` | None | Test roll by 45 degrees |
| `ship_tst_roll_90()` | None | Test roll by 90 degrees |
| `ship_tst_yaw_30()` | None | Test yaw by 30 degrees |
| `ship_tst_yaw_45()` | None | Test yaw by 45 degrees |
| `ship_tst_yaw_90()` | None | Test yaw by 90 degrees |

### Region Picker

| Method | Returns | Description |
|---|---|---|
| `start_region_picker()` | None | Launch background thread for screen region picking via right-click |
| `_wait_for_rightclick()` | `(x, y)` | Static method. Block until right mouse button pressed, return screen coordinates |
| `_region_picker_thread()` | None | Get ED window rect, capture two right-clicks, compute relative coords, draw overlay rect for 10s, display result |

### External Links

| Method | Returns | Description |
|---|---|---|
| `about()` | None | Open GitHub repo page in browser |
| `open_changelog()` | None | Open ChangeLog.md on GitHub in browser |
| `open_discord()` | None | Open Discord invite link in browser |
| `open_logfile()` | None | Open `autopilot.log` with system default handler |

### Update Checking

| Method | Returns | Description |
|---|---|---|
| `check_updates()` | None | Run `check_for_updates()`, log result to GUI |
| `check_for_updates(repo_path)` | `bool` | Git fetch + compare local HEAD vs origin/HEAD commit hashes. Returns True if different |

### GUI Generation

| Method | Returns | Description |
|---|---|---|
| `gui_gen(win)` | `Listbox` | Build entire GUI layout (top buttons, notebook tabs, status bar). Returns the log Listbox widget |
| `makeform(win, ftype, fields, r, inc, r_from, rto)` | `dict` | Create labeled form fields (checkbox/spinbox/entry) with tooltips. Returns dict mapping field name to widget |

## GUI Structure

**Layout**: Top buttons (Load All Settings, Save All Settings) > Notebook tabs > Status bar (status + jump count)

**Tabs**:

1. **Main** -- MODE section (Waypoint Assist checkbox), WAYPOINTS section (Load File, Load Last, file label), COMMODITIES section (Treeview with waypoint/type/commodity/qty columns, qty spinbox, Update/Save buttons), LOG section (scrollable Listbox with x/y scrollbars)

2. **Settings** -- AUTOPILOT (Sun Bright Threshold, Nav Align Tries, Jump Tries, Docking Retries, Wait For Autodock, Enable Randomness, Automatic logout), BUTTONS (DSS Button radio Primary/Secondary, Enable Hotkeys, Start FSD/Start SC/Stop All hotkey entries), FUEL (Refuel Threshold, Scoop Timeout, Fuel Threshold Abort), OVERLAY (Enable checkbox, X Offset, Y Offset, Font Size), KEYS (Activate Elite for each key, Modifier Key Delay, Default Hold Time, Repeat Key Delay), SHIP (PitchRate, YawRate, PitchFactor, YawFactor, SunPitchUp+Time, Calibrate Pitch Rate button, Calibrate Yaw Rate button), Save All Settings button

3. **Debug/Test** -- File Actions (Enable CV View, Restart, Exit), Help Actions (Check for Updates, View Changelog, Join Discord, About), Debug Settings (Debug/Info/Error radio buttons, Open Log File), Debug checkboxes (Debug Overlay, Debug OCR, Debug Images), Save All Settings, Pick Region button with result label, RPY Test grid (Roll/Pitch/Yaw at 30/45/90 degrees)

**Key UI Components**: Checkboxes (assist modes, debug flags, options), Spinboxes (numeric config), Entry fields (hotkeys), Radio buttons (debug level, DSS button), Treeview (commodity list), Status labels (status line, jump count)

## Dependencies

| Module | Purpose |
|---|---|
| `tkinter` (tk, ttk, filedialog, messagebox) | GUI framework |
| `sv_ttk` | Sun Valley dark/light theme for ttk |
| `pywinstyles` | Windows title bar color styling |
| `tktooltip.ToolTip` | Hover tooltips on form fields |
| `keyboard` | Global hotkey registration and capture |
| `webbrowser` | Open URLs in default browser |
| `subprocess` | Git commands for update checking |
| `pathlib.Path` | File path handling |
| `pynput.mouse` | Right-click capture for region picker (imported lazily) |
| `src.autopilot.ED_AP.EDAutopilot` | Core autopilot engine |
| `src.core.MousePt.MousePoint` | Mouse coordinate capture utility |
| `src.core.EDlogger.logger` | Logging utility |
| `src.screen.Screen.Screen` | Elite window rect detection (used in region picker) |

## Instance State

| Attribute | Type | Description |
|---|---|---|
| `root` | `tk.Tk` | Root tkinter window |
| `ed_ap` | `EDAutopilot` | Core autopilot engine instance |
| `mouse` | `MousePoint` | Mouse coordinate utility |
| `gui_loaded` | `bool` | True after GUI fully initialized |
| `log_buffer` | `queue.Queue` | Buffered log messages before GUI loads |
| `checkboxvar` | `dict[str, IntVar/BooleanVar]` | All checkbox state variables by name |
| `radiobuttonvar` | `dict[str, StringVar]` | All radio button state variables by name |
| `entries` | `dict[str, dict[str, Widget]]` | Nested dict of entry/spinbox widgets by group and field name |
| `lab_ck` | `dict` | Checkbox label widgets |
| `WP_A_running` | `bool` | Waypoint assist currently running flag |
| `cv_view` | `bool` | CV debug view enabled flag |
| `msgList` | `Listbox` | Log message listbox widget |
| `tooltips` | `dict[str, str]` | Tooltip text by field name |
| `wp_file_label` | `Label` | Shows loaded waypoint filename |
| `comm_tree` | `Treeview` | Commodity list treeview |
| `comm_qty_spin` | `Spinbox` | Commodity quantity editor |
| `region_result_label` | `Label` | Region picker result display |
| `status` | `Label` | Status line label |
| `jumpcount` | `Label` | Jump count label |

## Notes

- ~1075 lines, single class managing UI generation, callbacks, settings, hotkeys, and waypoint assist
- Callback system uses string-based message passing (`callback(msg, body)`) between EDAutopilot and GUI
- Log buffering handles initialization timing (messages logged before GUI is ready are queued)
- Update checking uses git CLI rather than GitHub API (commented-out requests code still present)
- Window is fixed size 1440x900, non-resizable, uses sv_ttk dark theme
- `restart_program()` references `stop_fsd()` and `stop_sc()` which are not defined in the current code (will error if called)
