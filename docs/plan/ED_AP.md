# ED_AP.py Optimization Plan

Current state: ~2200 lines, 12 methods over 50 lines, scattered magic numbers,
duplicate patterns, dead code.

## Priority 1: Dead Code Removal (safe, zero risk)

### Unused import
- `import random` (line 10) -- never called anywhere

### Unused config + setter
- `"EnableRandomness"` config default -- stored but never acted on
- `set_randomness()` -- just stores the flag, nothing reads it

### Old test methods (replaced by _enabled flag pattern)
- `ship_tst_roll(angle)` -- GUI calls commented out, replaced by `ship_tst_roll_enabled`
- `ship_tst_yaw(angle)` -- same
- `ship_tst_pitch(angle)` -- same
- `ship_tst_pitch_new(angle)` -- same (also commented out in GUI)
- `ship_tst_roll_new(angle)` -- same
- `ship_tst_yaw_new(angle)` -- same
- GUI in EDBob.py has commented-out calls to all 6 -- clean those comments too

### Commented-out fine align block in compass_align
- 6 lines of commented code (was arc detection + fine align call)
- Methods `is_target_arc_visible()`, `target_fine_align()`, `nudge_align()` are
  only reachable from this commented block -- candidates for removal if fine align
  is permanently disabled

## Priority 2: Duplicate Pattern Consolidation

### engine_loop() assist handlers (3x identical pattern)
SC Assist, Waypoint Assist, DSS Assist each have:
```python
try:
    self.xxx_assist(...)
except StopAssist:
    logger.debug("Caught stop exception")
except Exception as e:
    logger.exception("XXX trapped generic")
    if self._game_lost():
        continue
```
Extract to `_run_assist(name, func, *args)`.

### Debug snapshot code (2x identical)
`dock()` lines ~891-901 and `sc_assist()` lines ~1763-1773:
```python
if self.DEBUG_SNAP:
    try:
        snap = scr_reg.capture_region(self.scr, 'center_normalcruise')
        ...
        cv2.imwrite(...)
    except Exception as e:
        logger.warning(f"Debug snapshot failed: {e}")
```
Extract to `_debug_snap(scr_reg, label)`.

### Evasion sequences in sc_assist()
Body proximity evasion and occlusion evasion are nearly identical:
pitch up N degrees, cruise for M seconds, pitch down. Extract to
`_evade_pitch(degrees, cruise_time)`.

## Priority 3: Method Splitting (biggest methods) -- DONE

### get_nav_offset() -- 185 lines -> 23-line orchestrator + 5 helpers
Split into:
- `_capture_compass(scr_reg)` -> (bgr, hsv, orange_mask, w, h)
- `_detect_ring_center(scr_reg, orange_mask, w, h)` -> (cx, cy, r)
- `_detect_nav_dot(hsv, orange_mask, w, h)` -> (cx, cy, z, mask, contours)
- `_calc_nav_angles(dot_cx, dot_cy, ring_cx, ring_cy, ring_r, z)` -> offset dict
- `_save_compass_debug(...)` -> debug image output
- `get_nav_offset()` is now a thin orchestrator

### compass_align() -- 120 lines -- SKIPPED
After Priority 2, flip logic is 20 lines. Extracting adds parameter passing
overhead for minimal gain. The method reads fine as-is.

### sc_assist() -- 170 lines -- SKIPPED
After `_evade_pitch` extraction (Priority 2), the evasion code is 1 line each.
Setup and loop share local state. Splitting adds complexity, not clarity.

### engine_loop() -- DONE in Priority 2
`_run_assist()` consolidation already shrank it.

## Priority 4: Magic Numbers -> Constants -- DONE

Only replaced values appearing 3+ times with same purpose:

| Constant | Value | Occurrences | Context |
|----------|-------|-------------|---------|
| `BOOST_SETTLE` | 4s | 4x | after UseBoostJuice in dock + undock |
| `UNDOCK_SETTLE` | 5s | 4x | waits during waypoint_undock sequences |

Skipped (different purposes at each site):
- `sleep(2)` x6: retry waits, key settle, dock wait -- too varied
- `sleep(0.5)` x5: throttle settle, null check, dss poll -- too varied
- `sleep(3)` x2, `sleep(4.5)` x1, `sleep(1)` x2: too few or single-use

## Priority 5: Config Cleanup -- DONE

### Removed
- `"EnableRandomness"` -- removed in Priority 1
- `"DiscordWebhook"` / `"DiscordWebhookURL"` / `"DiscordUserID"` -- never implemented, removed
- `"OverlayTextEnable"` etc -- already removed in milestone commit
- `"Debug_ShowCompassOverlay"` etc -- already removed in milestone commit

## Execution Order

Do these as separate commits, each independently testable:

1. Dead code removal (Priority 1) -- smallest diff, zero risk
2. Duplicate consolidation (Priority 2) -- medium diff, low risk
3. Method splitting (Priority 3) -- larger diff, test after each split
4. Magic numbers (Priority 4) -- mechanical, low risk
5. Config cleanup (Priority 5) -- needs GUI check for bound fields

## NOT Doing

- Don't refactor `__init__()` -- it's long but straightforward, splitting adds complexity
- Don't refactor `load_config()` -- same reason
- Don't abstract the alignment math -- it's tuned and fragile, leave it readable
- Don't touch `_align_axis()` internals -- it works, the complexity is inherent
