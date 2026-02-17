# MenuNav.py

**Location:** `src/ed/MenuNav.py`

## Purpose

Consolidated menu/UI navigation functions for Elite Dangerous. Single source of truth for all menu key sequences. Replaces scattered menu navigation across ED_AP, EDNavigationPanel, EDStationServicesInShip, and EDShipControl with clean, reusable stateless functions.

## Dependencies

- `EDKeys` (keys param) -- sends keypresses to ED
- `StatusParser` (status_parser param) -- reads gui_focus from Status.json
- `EDAP_data` -- GuiFocus constants

## Functions

All functions are module-level (no class). They take `keys` and `status_parser` as first params (except where noted).

### `goto_cockpit(keys, status_parser) -> bool`
Sends `UI_Back` repeatedly until `gui_focus == NoFocus`. Safe to call when already in cockpit.

### `realign_cursor(keys, hold=3)`
Holds `UI_Up` to move cursor to the top of any menu list. Default hold=3 seconds.

### `refuel_repair_rearm(keys, status_parser)`
From docked station menu: realigns to top (Refuel), selects Refuel, moves right to Repair and selects, moves right to Rearm and selects, then returns to cockpit view.

### `open_station_services(keys, status_parser) -> bool`
From docked menu: goes to cockpit, realigns, navigates down to Station Services. Returns True if GuiFocus == StationServices within 15s timeout.

### `undock(keys, status_parser)`
From docked menu: goes to cockpit, realigns to top, navigates down 2 rows to Auto Undock, selects.

### `open_nav_panel(keys, status_parser) -> bool`
Sends `FocusLeftPanel`, waits for gui_focus == ExternalPanel (3s timeout). Returns success.

### `close_nav_panel(keys)`
Sends `UI_Back` to close nav panel.

### `activate_sc_assist(keys, status_parser, is_target_row_fn, cb=None) -> bool`
Opens nav panel, scrolls to top, steps down row-by-row calling `is_target_row_fn(seen_bracket)` to detect target. On match: selects row, navigates right to SC Assist button, selects, closes panel.

### `request_docking(keys, status_parser) -> bool`
Opens nav panel, cycles 2 tabs to Contacts, selects action on first entry (UI_Right + UI_Select), cycles back 2 tabs, closes panel.

### `transfer_all_to_colonisation(keys)`
Transfers all cargo to a colonisation/construction ship. Assumes the construction services screen is already open. Navigates into the table, selects TRANSFER ALL, confirms, and exits.

## Delegation Map

All callers delegate their menu key sequences to MenuNav:

| Caller | Method | Delegates to |
|---|---|---|
| `EDShipControl` | `goto_cockpit_view()` | `goto_cockpit()` |
| `EDNavigationPanel` | `activate_sc_assist()` | `activate_sc_assist()` |
| `EDNavigationPanel` | `request_docking()` | `request_docking()` |
| `EDNavigationPanel` | `hide_panel()` | `goto_cockpit()` |
| `EDStationServicesInShip` | `goto_station_services()` | `open_station_services()` |
| `EDStationServicesInShip` | `goto_construction_services()` | `goto_cockpit()` + `realign_cursor()` |
| `EDStationServicesInShip` | `sell_to_colonisation_ship()` | `transfer_all_to_colonisation()` |
| `ED_AP` | `undock()` | `undock()` |
| `ED_AP` | `dock()` (refuel block) | `refuel_repair_rearm()` |

## Not in MenuNav

- `sell_commodity` / `buy_commodity` -- business logic with market data, cursor tracking, OCR. Stays in `CommoditiesMarket`.
- Galaxy map, system map, fleet carrier transfers -- stay in their current files for now.

## Menu Layout Reference (Docked Station)

```
Row 0: Refuel  |  Repair  |  Rearm    (horizontal navigation with UI_Right)
Row 1: Station Services
Row 2: Auto Undock (Launch)
```
