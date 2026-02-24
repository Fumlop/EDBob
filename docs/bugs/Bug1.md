# Bug #1: Calibration loops endlessly when ED window not found

## Symptom

Clicking the calibration button when Elite Dangerous is not running causes an
endless loop. The engine_loop keeps re-entering `_run_assist` every second because
the calibrate flag is never cleared.

Secondary crash: even if the window check is added, `capture_region` throws
`KeyError` on `self.reg[region_name]` because screen regions aren't loaded
(no ED window means no resolution detected).

## Root Cause

1. `_run_assist` had no pre-check for the ED window existing.
2. `_game_lost()` only disabled sc/waypoint/dss flags, not calibration flags.
3. When `_run_assist` returned `True` (game lost), the engine_loop `continue`d
   but the `calibrate_normal_enabled` flag was still True -- infinite retry.
4. The `regions_loaded` guard in engine_loop only checked sc/waypoint assists,
   not calibration or DSS.

## Fix

### `_stop_all_assists()` -- new method
Extracted the "disable everything + notify GUI" pattern into one method.
Used by `_run_assist` (window check + crash handler) and `_game_lost()`.

### `_run_assist` -- window pre-check
Added `Screen.elite_window_exists()` check before running any assist.
If ED is not found, logs a message and calls `_stop_all_assists()`.

### `engine_loop` -- extended regions guard
The `regions_loaded` guard now covers all assists including DSS and calibration.

## Files Changed

- `src/autopilot/ED_AP.py`
