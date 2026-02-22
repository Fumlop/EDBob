# ED_AP.py -- Core Autopilot Engine

## Purpose

Main autopilot engine. Coordinates autonomous navigation, docking, trading, and ship control.
Lives in `src/autopilot/ED_AP.py`. Entry point is `EDAutopilot` class, instantiated by GUI.

## Architecture

- Single class `EDAutopilot` runs in a background thread (`engine_loop`)
- Uses `EDAP_Interrupt` exception to cleanly stop execution
- Callback system (`ap_ckb`) for GUI updates and logging
- State driven by ED journal events + screen capture analysis

## Module-Level Functions

| Function | Description |
|---|---|
| `read_json_file(filepath)` | Load JSON file, return dict or None |
| `write_json_file(data, filepath)` | Write dict to JSON file, return bool |
| `scale(inp, in_min, in_max, out_min, out_max)` | Linear range mapping |
| `delete_old_log_files()` | Delete .log files older than 5 days |
| `strfdelta(tdelta, fmt, inputtype)` | Format timedelta as string |
| `get_timestamped_filename(prefix, suffix, extension)` | Timestamped filename with millis |
| `dummy_cb(msg, body)` | No-op callback for testing |
| `main()` | Test harness entry point |

## Enums

| Enum | Values | Description |
|---|---|---|
| `EDAP_Interrupt` | Exception | Raised to stop assist execution cleanly |
| `ScTargetAlignReturn` | Lost=1, Found=2, Disengage=3 | SC target alignment result |

## Class Constants

### Alignment Thresholds

| Constant | Value | Description |
|---|---|---|
| `ROLE_YAW_PITCH_CLOSE` | 6.0 deg | Roll close enough to centerline |
| `ROLE_TRESHHOLD` | 8.0 deg | Min yaw offset before coarse roll |
| `ALIGN_CLOSE` | 4.0 deg | Compass convergence threshold |
| `ALIGN_SETTLE` | 2.0 s | Settle time after correction before next read |
| `ALIGN_TIMEOUT` | 25.0 s | Max time per axis alignment |
| `FINE_ALIGN_CLOSE` | 2.0 deg | Target circle "already aligned" |
| `FINE_ALIGN_OK` | 3.0 deg | Target circle "close enough" after correction |

### Key Hold Timing

| Constant | Value | Description |
|---|---|---|
| `MIN_HOLD_TIME` | 0.50 s | Minimum key hold for alignment moves |
| `MAX_HOLD_TIME` | 4.0 s | Maximum key hold for alignment moves |
| `KEY_WAIT` | 0.125 s | Key input settle time |

### Target Circle Detection

| Constant | Value | Description |
|---|---|---|
| `TARGET_CIRCLE_R_MIN` | 44 px | HoughCircles min radius at 1920x1080 |
| `TARGET_CIRCLE_R_MAX` | 48 px | HoughCircles max radius at 1920x1080 |
| `MIN_ARC_PIXELS` | 100 | Min orange pixels for arc visibility |
| `ARC_STD_THRESHOLD` | 12 | Radius std threshold for arc shape |

### SC Assist Detection

| Constant | Value | Description |
|---|---|---|
| `SC_ASSIST_GONE_RATIO` | 0.50 | Cyan ratio below this = SC Assist gone |
| `SC_ASSIST_CHECK_INTERVAL` | 3 s | Interval between SC Assist gone checks |
| `SC_SETTLE_TIME` | 5 s | Settle time after SC Assist engage |

### Maneuver Angles and Timing

| Constant | Value | Description |
|---|---|---|
| `HALF_TURN` | 180.0 deg | Flip when target behind |
| `QUARTER_TURN` | 90 deg | Break deadlock pitch |
| `OCCLUSION_PITCH` | 65 deg | Pitch for body occlusion evasion |
| `BODY_EVADE_PITCH` | 90 deg | Full body evasion pitch |
| `PASSBODY_TIME` | 25 s | Cruise time passing occluding body |
| `DOCK_PRE_PITCH` | 1.0 s | Pitch up time before boost to station |
| `ZERO_THROTTLE_RATE_FACTOR` | 0.60 | Turn rate multiplier at 0% throttle |

### Nudge Alignment

| Constant | Value | Description |
|---|---|---|
| `NUDGE_SAMPLES` | 5 | Samples for nudge consensus |
| `NUDGE_HOLD` | 0.4 s | Hold time for nudge corrections |
| `NUDGE_BOTH_THRESHOLD` | 5.0 deg | Threshold to nudge both axes |

### Debug Flags

| Flag | Default | Description |
|---|---|---|
| `DEBUG_SNAP` | False | Save debug screenshots to debug-output/ |
| `DEBUG_TARGET_CIRCLE` | True | Verbose logging for target circle detection + fine align. Prefix: `[TGT_CIRCLE]` and `[TGT_ALIGN]` |

## EDAutopilot Methods

### Initialization and Config

| Method | Returns | Description |
|---|---|---|
| `__init__(cb, doThread)` | None | Init autopilot, load configs, create subcomponents, start engine thread |
| `load_config()` | None | Load AP.json with defaults for missing keys |
| `update_config()` | None | Save current config to AP.json |
| `load_ship_configs()` | None | Load ship_configs.json |
| `load_ship_configuration(ship_type)` | None | Load ship config with 3-tier priority: user custom > defaults > hardcoded |
| `update_ship_configs()` | None | Save current ship rates to ship_configs.json |
| `process_config_settings()` | None | Push config changes to subclasses |
| `@property ocr` | OCR | Lazy-load OCR instance |

### Compass Navigation (navball)

These detect the cyan dot on the compass to determine where the nav target is.

| Method | Returns | Description |
|---|---|---|
| `get_nav_offset(scr_reg)` | dict or None | Get navball dot position as roll/pit/yaw degrees. Uses HoughCircles for ring center, cyan color filter for dot. Returns `{x, y, z, roll, pit, yaw}` where z=-1 means behind. |
| `have_destination(scr_reg)` | bool | Check if compass is visible on screen |
| `compass_align(scr_reg)` | bool | Full compass alignment sequence: flip if behind, coarse roll, yaw+pitch fine align, 3-of-3 verify, optional target_fine_align |
| `_roll_to_centerline(scr_reg, off, close)` | dict or None | Coarse roll to vertical centerline |
| `_yaw_to_center(scr_reg, off, close)` | dict or None | Yaw to horizontal center |
| `_pitch_to_center(scr_reg, off, close)` | dict or None | Pitch to vertical center |
| `_align_axis(scr_reg, axis, off, close, timeout)` | dict or None | Generic single-axis alignment loop with timeout |
| `_avg_offset(scr_reg, get_offset_fn)` | dict or None | 3-of-3 average for jitter filtering |
| `nudge_align(scr_reg)` | bool | Minimal 5-sample nudge correction on worst axis |

### Target Circle Detection (fine align)

These detect the big orange target circle around stations for precise centering.

| Method | Returns | Description |
|---|---|---|
| `_find_target_circle(image_bgr)` | (cx,cy) or None | Find orange target arc using HoughCircles with radius bounds 44-48px. Ignores nearby text. |
| `get_target_offset(scr_reg)` | dict or None | Convert target circle center to pit/yaw degrees from screen center |
| `is_target_arc_visible(scr_reg)` | bool | Check if orange arc visible (contour radius std < threshold) |
| `target_fine_align(scr_reg)` | bool | Precise alignment using target circle: single pitch then yaw correction at 50% approach rate, 3-of-3 verify |

### Axis Helpers

| Method | Returns | Description |
|---|---|---|
| `_roll_on_centerline(roll_deg, close)` | bool | Static: check if dot near 0 or +-180 deg |
| `_get_dist(axis, off)` | int | Ceil'd distance to target for axis |
| `_is_aligned(axis, off, close)` | bool | Check if aligned on given axis |
| `_axis_max_rate(axis)` | float | Get deg/s rate for axis from config |
| `_axis_pick_key(axis, deg)` | str | Pick correct key direction for axis correction |
| `_move_axis(axis, deg)` | None | Send key hold for given degrees on axis |

### FSD Jump Sequence

| Method | Returns | Description |
|---|---|---|
| `do_route_jump(scr_reg)` | None | Single FSD jump: sun avoid, align, jump, position |
| `jump(scr_reg)` | None | Execute FSD charge + jump, wait for hyperspace completion |
| `mnvr_to_target(scr_reg)` | None | Sun avoid + compass align + start FSD charge |
| `sun_avoid(scr_reg)` | bool | Pitch up if sun ahead, return True if avoidance ran |
| `is_sun_dead_ahead(scr_reg)` | bool | Check sun brightness > 5% |
| `position(scr_reg, sun_was_ahead)` | bool | Pass star with SCO boost, recover heading |

### Supercruise Navigation

| Method | Returns | Description |
|---|---|---|
| `sc_assist(scr_reg, do_docking)` | None | Full SC Assist flow: align, activate via nav panel, monitor for drop, dock |
| `sc_target_align(scr_reg)` | ScTargetAlignReturn | Align to target in SC, monitor for disengage/lost/obscured |
| `supercruise_to_station(scr_reg, station_name)` | bool | Navigate SC to named station |
| `is_sc_assist_gone(scr_reg)` | bool | 3-of-3 check if SC Assist indicator disappeared |
| `occluded_reposition(scr_reg)` | None | Reposition when target blocked by planet body |
| `sc_engage()` | bool | Enter supercruise after clearing masslock |
| `wait_masslock_clear(max_checks)` | None | Boost and wait until masslock clears |

### Docking and Station

| Method | Returns | Description |
|---|---|---|
| `dock()` | bool | Docking sequence: boost toward station, request docking, wait for autodock, refuel/repair |
| `undock()` | None | Menu undock action |
| `request_docking()` | None | Request docking from nav panel |
| `waypoint_undock_seq()` | None | Full undock sequence for waypoint assist (undock, pitch clear, boost, SC engage) |

### Assist Mode Control

| Method | Returns | Description |
|---|---|---|
| `waypoint_assist(keys, scr_reg)` | None | Main waypoint loop: process waypoints, jump, SC navigate, trade |
| `dss_assist()` | None | DSS scan loop (unused, stub) |
| `set_sc_assist(enable)` | None | Toggle SC assist mode |
| `set_waypoint_assist(enable)` | None | Toggle waypoint assist mode |
| `set_dss_assist(enable)` | None | Toggle DSS assist mode |
| `check_stop()` | None | Raise EDAP_Interrupt if stop requested |
| `interdiction_check()` | bool | Check for and handle interdiction |

### Speed Control

| Method | Returns | Description |
|---|---|---|
| `_set_speed(percent, repeat)` | None | Generic speed setter (0/25/50/100) using status flags |
| `set_speed_0(repeat)` | None | Full stop |
| `set_speed_25(repeat)` | None | 25% throttle |
| `set_speed_50(repeat)` | None | 50% throttle (blue zone) |
| `set_speed_100(repeat)` | None | Full throttle |

### Ship Testing / Calibration

| Method | Returns | Description |
|---|---|---|
| `_ship_tst_axis_calibrate(axis)` | None | Generic axis calibration: move, measure, compute rate |
| `ship_tst_pitch(angle)` | None | Test pitch by angle degrees |
| `ship_tst_pitch_new(angle)` | None | Calibrate pitch rate |
| `ship_tst_roll(angle)` | None | Test roll by angle degrees |
| `ship_tst_roll_new(angle)` | None | Calibrate roll rate |
| `ship_tst_yaw(angle)` | None | Test yaw by angle degrees |
| `ship_tst_yaw_new(angle)` | None | Calibrate yaw rate |
| `roll_clockwise_anticlockwise(deg)` | None | Roll by deg degrees |
| `pitch_up_down(deg)` | None | Pitch by deg degrees |
| `yaw_right_left(deg)` | None | Yaw by deg degrees |

### Settings Toggles

| Method | Returns | Description |
|---|---|---|
| `set_cv_view(enable, x, y)` | None | Toggle OpenCV debug window |
| `set_randomness(enable)` | None | Toggle random delays (anti-detection) |
| `set_activate_elite_eachkey(enable)` | None | Toggle Elite window focus per keypress |
| `set_automatic_logout(enable)` | None | Toggle auto-logout when done |
| `set_overlay(enable)` | None | Toggle overlay text |
| `set_log_error(enable)` | None | Set log level ERROR |
| `set_log_info(enable)` | None | Set log level INFO |
| `set_log_debug(enable)` | None | Set log level DEBUG |

### UI and Lifecycle

| Method | Returns | Description |
|---|---|---|
| `update_overlay()` | None | Draw overlay data on ED window |
| `update_ap_status(txt)` | None | Update status text in overlay + callback |
| `draw_match_rect(img, pt1, pt2, color, thick)` | None | Draw decorative match rectangle |
| `engine_loop()` | None | Main thread loop: runs active assist mode, handles interrupts |
| `quit()` | None | Clean shutdown: stop thread, close overlay |

## Key Workflows

### Waypoint Assist (full trade route)

```
waypoint_assist() loop:
  for each waypoint:
    1. EDWayPoint selects galaxy map bookmark
    2. do_route_jump():  sun_avoid -> compass_align -> jump -> position
    3. supercruise_to_station() -> sc_assist():
       a. compass_align to target
       b. Activate SC Assist via nav panel
       c. Monitor: sc_target_align loop (check disengage/occluded)
       d. Drop from SC
    4. dock(): boost -> request_docking -> wait autodock -> refuel/repair
    5. EDWayPoint handles buy/sell commodities
    6. waypoint_undock_seq(): undock -> pitch clear -> boost -> sc_engage
```

### Compass Align (navball)

```
compass_align():
  loop (max tries):
    1. get_nav_offset() -> roll/pit/yaw from compass
    2. If target behind (z<0): pitch up to flip (max 3 attempts)
    3. If roll > threshold: _roll_to_centerline()
    4. Fine align: pitch then yaw (or yaw then pitch, larger axis first)
    5. _avg_offset() 3-of-3 verify
    6. If close: target_fine_align() using big orange circle
    7. nudge_align() for final correction
```

### Target Fine Align (HoughCircles)

```
target_fine_align():
  1. _find_target_circle(): HoughCircles on orange mask (r=44-48px)
  2. get_target_offset(): convert circle center to pit/yaw degrees
  3. Single pitch correction (50% approach)
  4. Single yaw correction (50% approach, re-read after pitch)
  5. _avg_offset() 3-of-3 final verify
```

## Dependencies

| Module | Purpose |
|---|---|
| `EDWayPoint` | Waypoint file loading, navigation sequencing, commodity trading |
| `EDJournal` | Journal event parsing (jump, dock, interdiction) |
| `EDKeys` | Keybind detection and key sending |
| `EDShipControl` | Ship control abstraction |
| `EDGalaxyMap` | Galaxy map bookmark navigation |
| `EDSystemMap` | System map bookmark navigation |
| `EDNavigationPanel` | Nav panel interaction (docking request, SC Assist) |
| `EDInternalStatusPanel` | Status panel parsing (fuel, shields) |
| `EDStationServicesInShip` | Station commodity market interaction |
| `Screen` / `Screen_Regions` | Screen capture and region definitions |
| `OCR` | Text recognition (lazy loaded) |
| `Overlay` | Debug overlay rendering |
| `StatusParser` | status.json flag parsing |
| `NavRouteParser` | Route plotting data |
| `EDGraphicsSettings` | FOV/resolution detection |

## Config Dicts

| Dict | Source | Contents |
|---|---|---|
| `self.config` | AP.json | All autopilot settings, UI offsets, hotkeys, thresholds |
| `self.ship_configs` | ship_configs.json | Per-ship RPY rates and SC factors |

## Notes

- ~2700 lines, single class -- the central hub that wires everything together
- Color-based detection throughout (HSV filtering), no template matching
- Target circle detection uses HoughCircles (not contours) to avoid text interference
- Thread-based: engine_loop runs continuously, EDAP_Interrupt for clean stop
- 0% throttle rate factor (0.60) applied to all alignment moves since ship turns slower at zero speed
