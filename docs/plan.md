# Improvement Plan -- EDAPGui Codebase

Full method-by-method analysis of all major modules. Grouped by priority and effort.

---

## Priority 1 -- High Impact, Reduces Bugs

### 1.1 Deduplicate Movement Methods (ED_AP.py)

`pitch_up_down`, `roll_clockwise_anticlockwise`, `yaw_right_left` are 3x ~45 lines of nearly identical code. Same lookup table interpolation, same speed_demand logic, same print() calls.

**Action:** Single `move_axis(axis, degrees)` method. ~20 lines. Axis config (key names, rate, lookup angles) in a dict.

**Files:** ED_AP.py (lines 1801-1943)

---

### ~~1.2 Deduplicate Calibration Methods~~ PARTIALLY DONE

`calibrate_rates()` and `_cal_recover()` deleted (dead code). `ship_tst_*` methods still exist for manual calibration UI.

---

### ~~1.3 Deduplicate Speed Setters~~ DONE

`_SPEED_CONFIG` dict + `_set_speed(percent, repeat)`. 4 original methods are one-liner wrappers. Fallback logic (25%->50%) preserved generically.

---

### ~~1.4 Deduplicate Module Checkers~~ DONE

`_has_module(modules, item_search, slot=None)` replaces 63 lines with 13. 4 original functions are one-liner wrappers. SCO slot filter preserved via `slot=` param.

---

### 1.5 Journal Buffer Timeout (EDJournal.py)

The `partial` buffer for split-read recovery has no timeout. If game hangs mid-write, buffer held forever.

**Action:** Add age tracking or discard partial after N iterations.

**Files:** EDJournal.py ship_state()

---

### 1.6 Thread Safety for Shared State (ED_AP.py)

`sc_sco_is_active`, `speed_demand`, `_sc_disengage_active` modified by background threads, read by main thread. No locking.

**Action:** Use `threading.Event` for flags, or at minimum document which vars are thread-shared.

**Files:** ED_AP.py

---

## Priority 2 -- Medium Impact, Improves Maintainability

### 2.1 Break Up Giant Methods

| Method | Lines | Should be |
|--------|-------|-----------|
| `parse_line` (EDJournal) | 245 | Event handler dict/registry |
| `sc_target_align` | 195 | Split: detect, align loop, correction |
| `get_nav_offset` | 168 | Split: YOLO detect, color filter, math, debug |
| `sc_assist` | 157 | Split: main loop, evasion helper, docking |
| `engine_loop` | 122 | Extract assist dispatch, ship detection |
| `waypoint_undock_seq` | 115 | Extract per-station-type undock methods |
| `execute_trade` (EDWayPoint) | 230 | Split: sell phase, buy phase, sync |
| `waypoint_assist` (EDWayPoint) | 193 | Split: jump loop, dock loop, trade |
| `gui_gen` (EDAPGui) | 260 | Split per-tab methods |
| `load_config` | 127 | Schema-based defaults with validation |

### 2.2 Extract SC Assist Evasion Helper (ED_AP.py)

Body approach evasion and occlusion evasion are nearly identical pitch-up-fly-past-realign blocks.

**Action:** Single `_sc_evasion(scr_reg, reason_msg)` method.

**Files:** ED_AP.py sc_assist

---

### 2.3 Config Schema Validation (ED_AP.py)

`load_config` has 55+ `if key not in cnf: cnf[key] = default` lines. No type or range validation.

**Action:** Define config schema as dict with defaults, types, and ranges. Single validation loop.

**Files:** ED_AP.py (lines 253-379)

---

### 2.4 Station Type Detection as Dict (EDJournal.py)

`check_station_type` is 50+ lines of if/elif chains. Most cases are simple string -> enum mappings.

**Action:** Dict mapping for simple cases, functions for special cases (ColonisationShip, etc.).

**Files:** EDJournal.py (lines 143-194)

---

### ~~2.5 Waypoint Validation Schema~~ DONE

Two field sets (`_GLOBAL_FIELDS`, `_WAYPOINT_FIELDS`) + 4-line loop replaces 50 lines of manual checks. Also fixed pre-existing bug where `s=None` would crash the validation loop.

---

### 2.6 Extract Commodity Buy/Sell Common Logic (EDWayPoint.py + EDStationServicesInShip.py)

`execute_trade` has duplicated buy loops (lines 386-417 vs 418-445). `buy_commodity` and `sell_commodity` in EDStationServicesInShip share similar patterns.

**Action:** Extract shared helpers: market lookup, quantity validation, journal confirmation wait.

**Files:** EDWayPoint.py, EDStationServicesInShip.py

---

### 2.7 Hardcoded Path Consolidation (EDWayPoint.py)

`'./waypoints/' + Path(self.filename).name` appears 5 times.

**Action:** Property or helper method `self._waypoint_path`.

**Files:** EDWayPoint.py (lines 148, 192, 246, 376, 475)

---

### 2.8 Standardize Logging (All files)

Mixed patterns:
- `logger.info/debug/warning/error`
- `self.ap_ckb('log', ...)` callbacks
- `self.ap_ckb('log+vce', ...)` for voice
- `print()` statements (12+ occurrences)

**Action:** Remove all `print()` calls, replace with logger. Document when to use `ap_ckb` (user-facing messages) vs `logger` (debug/diagnostics).

**Files:** ED_AP.py, EDJournal.py, EDKeys.py, EDWayPoint.py

---

### 2.9 Overlay Thread Safety (Overlay.py)

Module-level `lines`, `text`, `quadrilaterals` dicts modified from multiple threads without synchronization. `overlay_paint` and `wndProc` iterate these while other threads modify them.

**Action:** Use `threading.Lock` around dict access, or use thread-safe queue for overlay commands.

**Files:** Overlay.py

---

## Priority 3 -- Low Impact, Code Quality

### 3.1 Remove Dead Code

- Commented-out power calculations in movement methods
- `ship_tst_pitch_calc_power` (77 lines, abandoned)
- Old `ship_tst_pitch/roll/yaw` (superseded by `_new` versions)
- Commented `main()` test code in ED_AP.py
- Commented TODO in EDJournal.py parse_line (StarClass)
- `lock_destination` in EDNavigationPanel.py (deprecated OCR)

### 3.2 Fix Typos in Config Keys

- `'FuelThreasholdAbortAP'` -> `'FuelThresholdAbortAP'` (with migration)
- `'SunPitchUp+Time'` -> `'SunPitchUpTime'`

### 3.3 Bare Except Cleanup

Replace `except:` and `except Exception:` with specific exceptions:
- EDJournal.py parse_line (lines 521-524) -- catches everything including KeyboardInterrupt
- EDAPGui.py entry_update (line 507)
- EDAPGui.py log_msg (line 408)
- EDJournal.py FuelCapacity parsing (lines 436-442)
- EDJournal.py jumps_remains (lines 470-473)

### 3.4 Atomic File Writes

`write_waypoints`, `write_construction`, config saves -- all write directly. If crash mid-write, file corrupted.

**Action:** Write to temp file, then rename (atomic on same filesystem).

### 3.5 StatusParser Duplicate Flag Methods

`translate_flags` and `translate_flags2` are 36 and 32 individual bitwise checks. Should be a loop over a flag definitions list.

### 3.6 EDKeys Init Verbosity

175+ lines of repetitive hotkey conflict checking. Should loop over a list of key names.

### 3.7 Construction Depot Station Name Bug (EDJournal.py)

Line 546: falls back to `dic.get('MarketID')` when station not found -- stores market ID number as station name.

**Action:** Use `dic.get('StationName', str(mrk))` instead.

---

## ~~Priority 0 -- Replace YOLO with Fixed-Region Detection~~ DONE

YOLO removed. Screen regions loaded from `configs/screen_regions/res_{w}_{h}/default.json`.
`Screen_Regions` loads from JSON config, supports per-ship overrides via `reload_regions(ship_type)`.
`get_nav_offset()` uses fixed compass region directly. `ultralytics` and `MachLearn` imports removed.

---

## Completed Items

- ~~1.5 Journal buffer timeout~~ -- partial line buffering + split-read recovery
- ~~1.6 Thread safety~~ -- threading.Event replaces ctypes, check_stop() at 12 points
- ~~2.2 SC evasion helper~~ -- occlusion rewritten (blue SC Assist indicator)
- ~~2.4 Station type dict~~ -- check_station_type now uses dict lookup + 2 special cases
- **Journal reopen bug** -- open_journal() now sets current_log (was reopening every second)
- **Sun avoidance flip** -- compass_align always pitches UP when target behind (away from star)
- **_align_axis bail on z<0** -- stops pitching into pit=180 loop, returns to compass_align for flip
- **SC Assist indicator region** -- fixed absolute pixels [940,350]-[1000,400], threshold 0.05
- **Refuel/repair nav** -- 2x UI_Left after rearm to return cursor before leaving
- **Log rotation** -- fresh log per app start, rotate max 5 backups, 10MB cap
- **Journal single open** -- only find newest journal at startup, tail it forever
- ~~0.1 YOLO removal~~ -- fixed-region config, `Screen_Regions` loads from JSON, ML imports removed
- **Sun avoid rework** -- 25% throttle, 45deg initial pull-up, 15deg steps, reserve, 100% fly-by, pitch-down recovery after position()
- **Masslock clearing** -- unified `wait_masslock_clear()` method, boost every 5s, used in `sc_engage()`
- **sc_engage simplified** -- removed `boost` param, always clears masslock, SCO burst 5s, speed 0 after
- **Dead code removed** -- `refuel()`, `calibrate_rates()`, `_cal_recover()`, gear retract poll
- **Dock simplified** -- single docking attempt + 30s retry, journal-based autodock wait, no distance retry loop
- **Timing optimizations** -- undock polls (sleep 5 x12, sleep 3 x20), jump pre-FSD 0.2s, window focus removed, journal catch-up 4s->2s
- **2-of-3 dot voting** -- compass dot detection in `sc_target_align` uses 2-of-3 vote instead of sleep retries
- **MenuNav cleanup** -- `realign_cursor` 2x UI_Up, delays added between rapid key actions, request_docking 0.3s uniform

---

## Estimated Effort

| Item | Effort | Risk |
|------|--------|------|
| 1.1 Deduplicate movement | 1-2h | Low |
| 1.2 Deduplicate calibration | 1h | Low |
| 1.3 Deduplicate speed | 30min | Low |
| 1.4 Deduplicate module checkers | 30min | Low |
| 1.5 Journal buffer timeout | 15min | Low |
| 1.6 Thread safety | 2-3h | Medium |
| 2.1 Break up giant methods | 4-6h | Medium |
| 2.2 SC evasion helper | 30min | Low |
| 2.3 Config schema | 2-3h | Medium |
| 2.4 Station type dict | 1h | Low |
| 2.5 Waypoint schema | 1-2h | Low |
| 2.6 Buy/sell common logic | 2h | Medium |
| 2.7 Path consolidation | 15min | Low |
| 2.8 Standardize logging | 1-2h | Low |
| 2.9 Overlay thread safety | 1-2h | Medium |
| 3.x Code quality items | 2-3h total | Low |
