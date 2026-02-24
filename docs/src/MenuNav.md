# src/ed/MenuNav.py (243 lines)

Consolidated, stateless menu navigation functions. No class -- all functions
take `keys` (EDKeys) and `status_parser` (StatusParser) as parameters.

## Functions

| Function | Description |
|----------|-------------|
| `goto_cockpit(keys, sp)` | Close all menus, return to flight view |
| `realign_cursor(keys, sp)` | Move cursor to top of current list |
| `refuel_repair_rearm(keys, sp)` | Post-dock station services sequence |
| `open_station_services(keys, sp)` | Open station services menu |
| `undock(keys, sp)` | Launch sequence |
| `open_nav_panel(keys, sp)` | Open left panel |
| `close_nav_panel(keys, sp)` | Close left panel |
| `activate_sc_assist(keys, sp)` | Activate supercruise assist module |
| `request_docking(keys, sp)` | Send docking request via contacts |
| `transfer_all_to_colonisation(keys, sp)` | Transfer cargo to colonisation depot |

## Design

Stateless by design -- no instance needed, no side effects beyond key presses.
Each function polls `status_parser` to verify the menu state after actions.
