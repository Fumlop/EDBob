# MenuNav.py -- Consolidated Menu Navigation

## Purpose

Consolidated menu/UI navigation functions for Elite Dangerous. Single source of truth for all menu key sequences. Stateless module-level functions replace scattered menu navigation across ED_AP, EDNavigationPanel, EDStationServicesInShip, and EDShipControl.
Lives in `src/ed/MenuNav.py`.

## Functions

All functions are module-level (no class). They take `keys` (EDKeys) and `status_parser` (StatusParser) as first params unless noted otherwise.

| Function | Returns | Description |
|---|---|---|
| `goto_cockpit(keys, status_parser, max_tries=10)` | bool | Sends `UI_Back` repeatedly until `gui_focus == NoFocus`. Safe to call when already in cockpit. Returns False if max_tries exceeded. |
| `realign_cursor(keys)` | None | Holds `UI_Up` for 2s to move cursor to top of any menu list. |
| `refuel_repair_rearm(keys, status_parser)` | None | From docked menu: Refuel (top row), Right to Repair, Right to Rearm, then back to cockpit. |
| `open_station_services(keys, status_parser)` | bool | From docked menu: cockpit, realign, Down to Station Services, Select. Returns True if `GuiFocusStationServices` within 15s. |
| `undock(keys, status_parser)` | None | From docked menu: cockpit, realign, Down x2 to Auto Undock, Select. |
| `open_nav_panel(keys, status_parser)` | bool | Sends `FocusLeftPanel`, waits for `GuiFocusExternalPanel` (3s timeout). |
| `close_nav_panel(keys)` | None | Sends `UI_Back` to close nav panel. |
| `activate_sc_assist(keys, status_parser, is_target_row_fn, cb=None)` | bool | Opens nav panel, scrolls to top, steps down row-by-row (max 20) calling `is_target_row_fn(seen_bracket)`. On match: Select, Right to SC Assist, Select, close panel. |
| `request_docking(keys, status_parser)` | bool | Opens nav panel, cycles 2 tabs to Contacts, Right + Select on first entry, cycles back 2 tabs, closes panel. |
| `transfer_all_to_colonisation(keys)` | None | Keys-only param. Transfers all cargo to colonisation ship: navigate into table, TRANSFER ALL, Confirm, Exit. Assumes construction services screen is open. |

## Delegation Map

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

## Menu Layout Reference (Docked Station)

```
Row 0: Refuel  |  Repair  |  Rearm    (horizontal navigation with UI_Right)
Row 1: Station Services
Row 2: Auto Undock (Launch)
```

## Dependencies

| Module | Purpose |
|---|---|
| `EDAP_data` | `GuiFocusNoFocus`, `GuiFocusExternalPanel`, `GuiFocusStationServices` |
| `StatusParser` | Reads gui_focus from Status.json |
| `EDlogger` | Logging |

## Notes

- All functions are stateless -- no class needed
- `realign_cursor` uses 2s hold on `UI_Up` (not 3s as previously documented)
- `activate_sc_assist` walks max 20 rows before giving up
- `request_docking` cycles to Contacts tab (2 tabs right from Navigation)
- Not in MenuNav: buy/sell commodity logic (stays in `CommoditiesMarket`), galaxy/system map navigation
