# src/ship/Ship.py (692 lines)

The Ship is the "vehicle" -- it knows what it is, how fast it turns, how to steer,
and how to load/save its configuration. The autopilot (ED_AP) decides where to go;
Ship executes the physical movement.

## Class: Ship

### Identity and Modules (from journal events)

| Attribute | Source | Description |
|-----------|--------|-------------|
| `ship_type` | LoadGame/Loadout | Internal name, e.g. `'anaconda'` |
| `ship_size` | LoadGame/Loadout | `'S'`, `'M'`, `'L'` or `''` |
| `has_fuel_scoop` | Loadout | bool or None (None = not yet known) |
| `has_adv_dock_comp` | Loadout | bool or None |
| `has_std_dock_comp` | Loadout | bool or None |
| `has_sco_fsd` | Loadout | bool or None |
| `cargo_capacity` | Loadout | int |

### Fuel State (from journal events)

| Attribute | Source |
|-----------|--------|
| `fuel_level` | Any event with FuelLevel, FuelScoop |
| `fuel_capacity` | Any event with FuelCapacity |
| `fuel_percent` | Derived: `round(fuel_level / fuel_capacity * 100)` |
| `is_scooping` | True while FuelScoop events arrive and tank not full |

### Turn Rates and Flight Mode

Two rate sets stored: `_rates_normal` (measured at 50% throttle) and `_rates_sc`
(measured in supercruise at 0%). `update_flight_mode()` checks `FlagsSupercruise`
from status.json and swaps the active rates.

| Rate Attribute | Default | Per-mode |
|----------------|---------|----------|
| `pitchrate` | 33.0 deg/s | Yes |
| `rollrate` | 80.0 deg/s | Yes |
| `yawrate` | 8.0 deg/s | Yes |

`ZERO_THROTTLE_RATE_FACTOR = 0.60` -- applied in normal space at zero throttle
(SC calibration already measures at 0%, so no factor needed there).

### Movement Methods

```
send_pitch(deg, at_zero_throttle=False)  # Ship picks key + rate
send_roll(deg)                           # Ship picks key + rate
hold_time(axis, deg) -> float            # Returns seconds for timeout calc
```

ED_AP calls these instead of computing hold times itself.

### Alignment (compass-based)

Ship does the actual compass alignment loop. ED_AP provides the `get_offset_fn`.

```
align_axis(scr_reg, axis, off, close, timeout, get_offset_fn=...)
roll_to_centerline(scr_reg, off, close, get_offset_fn=...)
yaw_to_center(scr_reg, off, close, get_offset_fn=...)
pitch_to_center(scr_reg, off, close, get_offset_fn=...)
avg_offset(scr_reg, get_offset_fn) -> dict
```

### Calibration

`calibrate_rates(mode, scr_reg, get_offset_fn)` -- measures actual turn rates by
sending known-duration holds and reading compass displacement. Stores results in
the correct rate set (`_rates_normal` or `_rates_sc`). Persists to `ship_configs.json`.

### Config Persistence

Ship configs stored at `./configs/ship_configs.json`. Three-tier priority:
1. Per-ship overrides in `Ship_Configs[ship_type]`
2. SC lookup table `ship_rpy_sc_50` in EDAP_data
3. Global defaults (33/80/8)

Per-mode calibration stored as `Normalspace` and `Supercruise-zero` sub-dicts.

## Journal Event Integration

Ship registers callbacks via `register_journal_events(jn)`:

| Event | Handler | Updates |
|-------|---------|---------|
| `LoadGame` | `_on_load_game` | ship_type, ship_size |
| `Loadout` | `_on_loadout` | type, size, cargo, all modules |
| `_fuel_update` | `_on_fuel_update` | fuel_level, fuel_capacity, fuel_percent, is_scooping |

At registration time, `_sync_from_journal(jn.ship_state())` hydrates from the
journal's catchup data.

## Dependencies

- `src.core.EDAP_data` -- ship_size_map, ship_rpy_sc_50, flag constants
- `src.ed.EDJournal` -- get_ship_size, check_fuel_scoop, check_*_docking_computer, check_sco_fsd
- `src.core.EDlogger` -- logger

## Pure Functions (testable)

- `_scale(inp, in_min, in_max, out_min, out_max)` -- linear interpolation
- `_roll_on_centerline(roll_deg, close)` -- static method, checks if roll near 0/180
- `_axis_pick_key(axis, deg)` -- picks DirectInput key name for axis + direction
- `_get_dist(axis, off)` -- degrees remaining for an axis
- `_is_aligned(axis, off, close)` -- within threshold?
- `_update_fuel_percent()` -- derived fuel percentage
