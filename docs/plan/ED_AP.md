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

## Priority 3: Method Splitting (biggest methods)

### get_nav_offset() -- 185 lines
Split into:
- `_capture_compass(scr_reg)` -> returns upscaled BGR image
- `_detect_ring_center(compass_hsv, orange_mask, comp_w, comp_h)` -> returns (cx, cy, r)
- `_detect_nav_dot(compass_hsv, orange_mask, comp_w, comp_h)` -> returns (cx, cy, z)
- `_calc_nav_angles(dot_cx, dot_cy, ring_cx, ring_cy, ring_r, z)` -> returns offset dict
- Keep `get_nav_offset()` as thin orchestrator calling these 4

### compass_align() -- 131 lines
Split into:
- `_flip_if_behind(off, scr_reg)` -> pitches up, returns new offset or None
- Keep roll/pitch/yaw alignment inline (already delegates to helpers)

### sc_assist() -- 170+ lines
Split into:
- `_sc_assist_setup(scr_reg)` -> undock check, SC engage, nav panel, sun avoid
- `_sc_assist_loop(scr_reg)` -> main polling loop
- `_handle_body_proximity(scr_reg)` -> body evasion
- `_handle_occlusion(scr_reg)` -> occlusion evasion

### engine_loop() -- 125+ lines
Already covered by assist handler consolidation above. After that it should
be under 60 lines.

## Priority 4: Magic Numbers -> Constants

Scattered sleep values with no explanation. Group by purpose:

| Current | Where | Proposed Constant |
|---------|-------|-------------------|
| `sleep(2)` after key send | multiple | `KEY_SETTLE` or just use `ALIGN_SETTLE` |
| `sleep(4)` after boost | dock, position | `BOOST_SETTLE` |
| `sleep(4.5)` SCO burst | position | `SCO_BURST_TIME` |
| `sleep(0.5)` quick waits | multiple | `QUICK_SETTLE` |
| `sleep(3)` menu render | station services | `MENU_RENDER_WAIT` |
| `sleep(5)` undock sleeps | waypoint_undock | already long enough to warrant names |

Only do this where the same value appears 3+ times with same purpose.
Don't over-constant single-use sleeps.

## Priority 5: Config Cleanup

### Defaults that could be removed
- `"EnableRandomness"` -- dead feature, never implemented
- `"DiscordWebhook"` / `"DiscordWebhookURL"` / `"DiscordUserID"` -- "not implemented yet"

### Defaults that should stay but are questionable
- `"OverlayTextEnable"` etc -- already removed in uncommitted changes
- `"Debug_ShowCompassOverlay"` etc -- already removed in uncommitted changes

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
