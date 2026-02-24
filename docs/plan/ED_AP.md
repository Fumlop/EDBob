# ED_AP.py Refactoring Status

Started at ~2200 lines, now at ~1644 lines. Major architectural changes complete.

## Completed Work

### Phase 1: ED_AP Cleanup (earlier sessions)

- [x] **Dead code removal** -- random import, EnableRandomness, old test methods, commented fine-align
- [x] **Duplicate consolidation** -- `_run_assist()`, `_debug_snap()`, `_evade_pitch()`
- [x] **Method splitting** -- `get_nav_offset()` decomposed into 5 helpers
- [x] **Magic numbers** -- BOOST_SETTLE, UNDOCK_SETTLE extracted
- [x] **Config cleanup** -- Discord, Randomness, Overlay configs removed

### Phase 2: Ship Extraction

- [x] **Ship class created** (`src/ship/Ship.py`) -- identity, turn rates, steering, calibration
- [x] **Axis state moved to Ship** -- speed_demand, ZERO_THROTTLE_RATE_FACTOR, axis_max_rate
- [x] **Throttle/steering/calibration moved to Ship** -- alignment loops, calibrate_rates
- [x] **Movement delegation** -- ED_AP calls `ship.send_pitch(deg)` instead of computing hold times

### Phase 3: Journal Threading

- [x] **EDJournal threaded stream** -- background daemon thread, 200ms poll, event callbacks
- [x] **Event system** -- `on_event(name, cb)` / `_fire_event()`, synthetic `_fuel_update`
- [x] **Thread-safe writes** -- `set_field()` with lock
- [x] **Construction depot decoupled** -- fires via event callback, not inline in parse_line

### Phase 4: Ship Owns Properties

- [x] **Ship owns ship-property fields** -- type, size, modules, fuel, cargo
- [x] **Journal event handlers on Ship** -- LoadGame, Loadout, _fuel_update callbacks
- [x] **Catchup sync** -- `_sync_from_journal()` hydrates from journal dict at startup
- [x] **Flight-mode rate switching** -- `_rates_normal` / `_rates_sc`, auto-switch via status flags
- [x] **ED_AP reads Ship directly** -- `self.ship.has_fuel_scoop` instead of `jn.ship_state()`

### Phase 5: Robustness

- [x] **Crash-stop fix** -- assists disabled on unhandled exception, no silent restart
- [x] **Unit tests** -- 92 pure-function tests (EDJournal, Ship, Screen_Regions)

## Current Architecture

```
ED_AP (1644 lines) -- decision-maker, navigation logic
  |
  +-- Ship (692 lines) -- vessel: identity, rates, steering, fuel, modules
  |
  +-- EDJournal (641 lines) -- threaded journal stream, event callbacks
  |
  +-- Screen/Regions -- capture, color filters, region definitions
  |
  +-- Parsers -- status.json, navroute, cargo, market
  |
  +-- Panel readers -- nav panel, galaxy map, system map, station services
```

## Remaining Candidates (not urgent)

### Dead code check
- `is_target_arc_visible()`, `target_fine_align()`, `nudge_align()` -- only reachable
  from commented-out fine-align block. Remove if fine align is permanently disabled.

### Further Ship delegation
- Navigation state (target, status, location) stays on Journal -- correct for now
- If Journal grows unwieldy, could split nav state into a Route/Navigation class

### ED_AP still large
At 1644 lines ED_AP is manageable. The big methods (`compass_align`, `sc_assist`,
`dock`) share local state that resists extraction. Don't force it.

## NOT Doing

- Don't refactor `__init__()` -- long but straightforward
- Don't refactor `load_config()` -- same reason
- Don't abstract alignment math -- tuned and fragile
- Don't thread status.json -- tiny file, mod-time check is cheap
