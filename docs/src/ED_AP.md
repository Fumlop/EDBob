# ED_AP.py

## Purpose
Core autopilot engine for Elite Dangerous that coordinates autonomous navigation, ship control, and assistance systems. Implements intelligent flight assistance including FSD jumps, supercruise navigation, waypoint following, and docking/undocking sequences.

## Key Classes
- **EDAutopilot**: Main autopilot controller with multiple assistance modes and ship control capabilities
- **EDAP_Interrupt**: Exception class used to unroll call stack and stop execution cleanly
- **ScTargetAlignReturn**: Enum for target alignment states (Lost, Found, Disengage)
- **FSDAssistReturn**: Enum for FSD assist completion states (Failed, Partial, Complete)

## Key Methods

### Core Assistance Systems
- **do_route_jump(scr_reg)**: Single FSD jump: align, jump, honk, refuel, position, throttle 0. Used by waypoint loop for one-jump-at-a-time multi-system routes
- **sc_assist(scr_reg, do_docking=True)**: Supercruise navigation: sun avoid, compass align, activate SC Assist via nav panel, monitor for body obscuring (every 2.5s), wait for auto-drop
- **waypoint_assist(keys, scr_reg)**: Follow waypoint file sequence for autonomous trading routes
- **robigo_assist()**: Specialized flight assistance for Robigo Mines mission runs
- **afk_combat_loop()**: AFK combat automation with shield/fighter monitoring
- **dss_assist()**: Deep Space Scanner assistance

### Navigation & Targeting
- **get_nav_offset(scr_reg, disable_auto_cal=False)**: Calculate navigation point offset on compass
- **get_target_offset(scr_reg, disable_auto_cal=False)**: Calculate target reticle offset using color-based circle detection (orange normal, grey occluded)
- **_find_target_circle(image_bgr)**: HSV color filter + contour detection for target circle (replaces template matching)
- **compass_align(scr_reg)**: Align ship heading to navigation point
- **sc_target_align(scr_reg)**: Align ship to target object in supercruise
- **sun_avoid(scr_reg)**: Detect and avoid star hazards
- **position(scr_reg, did_refuel=True)**: Maintain optimal targeting position

### Docking & Station Operations
- **dock()**: Execute automated docking sequence
- **undock()**: Execute automated undock sequence with clearance
- **request_docking()**: Request docking clearance
- **waypoint_undock_seq()**: Special undock for waypoint missions
- **sc_engage(boost=False)**: Transition from supercruise to normal space

### Ship Control
- **ship_tst_roll(angle)**: Roll ship to specified angle
- **ship_tst_pitch(angle)**: Pitch ship to specified angle
- **ship_tst_yaw(angle)**: Yaw ship to specified angle
- **roll_clockwise_anticlockwise(deg)**: Roll control with inertia
- **pitch_up_down(deg)**: Pitch control with inertia
- **yaw_right_left(deg)**: Yaw control with inertia
- **refuel(scr_reg)**: Execute fuel scoop/scooping sequence
- **jump(scr_reg)**: Execute FSD jump

### Calibration & Monitoring
- **calibrate_target()**: Interactive target reticle calibration
- **calibrate_compass()**: Interactive compass calibration
- **calibrate_region(range_low, range_high, threshold, reg_name, templ_name)**: Generic template matching calibration
- **start_sco_monitoring()**: Monitor supercruise countdown
- **stop_sco_monitoring()**: Stop supercruise monitoring thread
- **have_destination(scr_reg)**: Check if navigation target exists
- **interdiction_check()**: Detect hostile interdiction attempts

### Configuration & State Management
- **load_config()**: Load AP.json configuration file
- **update_config()**: Save current config state to AP.json
- **load_ship_configs()**: Load ship-specific configuration overrides
- **load_ship_configuration(ship_type)**: Load settings for specific ship type
- **set_sc_assist(enable)**: Enable/disable supercruise assistance mode
- **set_waypoint_assist(enable)**: Enable/disable waypoint mode
- **set_robigo_assist(enable)**: Enable/disable Robigo mode
- **set_afk_combat_assist(enable)**: Enable/disable combat mode
- **set_dss_assist(enable)**: Enable/disable DSS mode
- **engine_loop()**: Main execution loop handling all assistance modes

### Utility & Debug
- **update_overlay()**: Render status overlay on screen
- **update_ap_status(txt)**: Update status text display
- **set_cv_view(enable, x, y)**: Enable debug OpenCV window
- **set_overlay(enable)**: Toggle overlay display
- **set_voice(enable)**: Toggle voice output
- **set_log_debug(enable)**: Toggle debug logging
- **quit()**: Cleanly shutdown autopilot

## State Management
State is managed through:
- **config dict**: Loaded from AP.json containing user settings, UI offsets, keybinds, voice settings
- **ship_configs dict**: Per-ship configuration overrides (compass_scale, yaw/roll/pitch rates)
- **Assistance mode flags**: Boolean flags track active assistance (sc_assist_enabled, waypoint_assist_enabled, etc.)
- **Derived state**: Navigation corrections (_nav_cor_x/_nav_cor_y), target alignment limits, FOV calculations
- **Ship state**: Current ship type, jump/refuel counters, ETA tracking
- **Overlay state**: AP status text, FSS detection results, debug display toggles

## Dependencies
- **Standard**: math, os, traceback, datetime, enum, random, string, tkinter
- **Computer Vision**: cv2, ultralytics (YOLO)
- **Elite Dangerous Game**: EDJournal, EDKeys, EDWayPoint, Screen, Screen_Regions, Image_Templates, StatusParser
- **Ship Control**: EDShipControl, EDStationServicesInShip, EDNavigationPanel, EDInternalStatusPanel
- **Navigation**: EDGalaxyMap, EDSystemMap, NavRouteParser, Overlay
- **Assistance**: AFK_Combat, Robigo, OCR, MachineLearning, TceIntegration
- **Utilities**: Voice, EDLoggerLogger, LocalizationManager
- **Configuration**: EDAPColonizeEditor (read/write JSON)

## Notes
- Large monolithic class (3600+ lines) handling multiple autopilot modes; primary execution hub
- Increasingly uses color-based detection (HSV filtering) over template matching for resolution independence
- SC Assist workflow: sun_avoid -> compass_align -> activate_sc_assist (nav panel) -> monitor loop with body avoidance (25% throttle, roll+pitch to evade, SC Assist re-aligns automatically)
- Thread-based architecture with engine_loop running continuously; uses EDAP_Interrupt exception for clean shutdown
- Extensive ship calibration requirements; compass/target alignment uses machine learning assistance
- State machine orchestrates multiple assistance modes with proper cleanup and mode transitions
- FOV calculations handle wide-aspect-ratio monitors with adaptive scaling
