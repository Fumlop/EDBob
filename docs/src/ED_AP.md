# src/autopilot/ED_AP.py (1644 lines)

Central autopilot controller. Owns all subsystems. Makes navigation decisions
and delegates ship movement to Ship.

## Class: EDAutopilot

### Ownership

EDAutopilot creates and owns:
- `EDJournal` -- journal stream (starts background thread)
- `Ship` -- vessel model (registers journal events)
- `Screen` -- screen capture
- `Screen_Regions` -- region definitions + filters
- `EDKeys` -- key bindings + sending
- `StatusParser` -- status.json reader
- `NavRouteParser` -- route file reader
- `EDNavigationPanel`, `EDGalaxyMap`, `EDSystemMap` -- UI panel readers
- `EDInternalStatusPanel`, `EDStationServicesInShip` -- station/panel readers
- `EDWayPoint` -- waypoint route manager

### Ship Property Proxies

ED_AP exposes ship properties via `_ship_proxy(attr)` descriptors for backward
compat with GUI code that reads `ap.pitchrate` etc.

### Engine Loop

`engine_loop()` runs on a kthread. Polls every ~1s:
1. Updates flight mode on Ship (`update_flight_mode()`)
2. Announces ship type changes to GUI
3. Dispatches active assist via `_run_assist()`

Only one assist runs at a time (blocking). On unhandled exception, all assists
are disabled and the user is notified (no silent restart).

### Assists

| Assist | Method | Trigger |
|--------|--------|---------|
| SC Assist | `sc_assist()` | In supercruise, navigates to station |
| Waypoint | `waypoint_assist()` | Multi-step route (jump, dock, trade, undock) |
| DSS | `dss_assist()` | Detailed surface scanner automation |
| Calibrate Normal | `calibrate_rates('normal')` | Measure turn rates in normal space |
| Calibrate SC | `calibrate_rates('sc')` | Measure turn rates in supercruise |

### Compass and Target Detection

| Method | Description |
|--------|-------------|
| `get_nav_offset(scr_reg)` | Reads compass: pitch, yaw, roll from orange dot |
| `get_target_offset(scr_reg)` | Reads target reticle: pitch, yaw |
| `compass_align(scr_reg)` | Full alignment loop: roll, yaw, pitch to nav target |
| `mnvr_to_target(scr_reg)` | Maneuver using target reticle instead of compass |

Compass detection pipeline:
1. `_capture_compass()` -- grab + HSV convert
2. `_detect_ring_center()` -- find compass ring via orange mask
3. `_detect_nav_dot()` -- find nav dot position + z-depth
4. `_calc_nav_angles()` -- convert pixel offsets to degrees

#### Navball spherical geometry (analysed 2026-02-25)

The navball is an orthographic projection of a sphere. A point at angle `theta`
projects to `sin(theta)` from center. `_calc_nav_angles()` correctly uses
`asin()` to recover pitch and yaw from the normalized dot position (lines 506-507).

Known coupling: yaw is computed as `asin(x)` but the true projection is
`x = sin(yaw) * cos(pitch)`. This underestimates yaw when pitch is large
(e.g. -9.3 deg error at pit=45/yaw=30). Doesn't matter in practice because:
- Alignment is iterative and re-reads after each correction
- Axes are aligned sequentially (pitch near zero when yaw is corrected)
- Calibration rates use the same arcsin units, so hold times are self-consistent

`get_target_offset()` (line 674) uses linear mapping for the main viewport
target circle. Technically should be `atan()` for rectilinear projection, but
error is small near center where the target reticle is used.

### Navigation

| Method | Description |
|--------|-------------|
| `position(scr_reg)` | Align to nav target, handle sun avoidance |
| `jump(scr_reg)` | Execute FSD jump sequence |
| `do_route_jump(scr_reg)` | One jump in a multi-jump route |
| `supercruise_to_station(scr_reg, name)` | SC to station, wait for drop |
| `sc_engage()` | Enter supercruise |

### Docking

| Method | Description |
|--------|-------------|
| `dock()` | Full docking sequence (request, align, approach) |
| `undock()` | Launch sequence |
| `request_docking()` | Send docking request via nav panel |
| `waypoint_undock_seq()` | Undock + clear station for waypoint routes |

### Delegation Pattern

ED_AP decides angles, Ship executes:

```python
# Old pattern (removed):
hold = angle / self.ship.pitchrate
self.keys.send('PitchUpButton', hold=hold)

# New pattern:
self.ship.send_pitch(angle)
```

For alignment, ED_AP passes `get_offset_fn` to Ship's alignment methods:
```python
self.ship.pitch_to_center(scr_reg, off, get_offset_fn=self.get_nav_offset)
```

### Error Handling

`_run_assist(name, func, *args)`:
- `StopAssist` exception -- clean stop, expected
- `_game_lost()` -- ED window gone, clean stop
- Any other exception -- disable ALL assists, notify user, do NOT restart

## Dependencies

Imports from nearly every module in the project. This is the integration point.

## Proxy Properties (for GUI backward compat)

pitchrate, rollrate, yawrate, yawfactor, ship_type, ship_configs
-- all delegate to `self.ship.*`
