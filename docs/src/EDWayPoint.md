# src/autopilot/EDWayPoint.py (676 lines)

Waypoint file management and multi-step route execution: jump, dock, trade, undock.

## Class: EDWayPoint

Loads waypoint JSON files that define trade routes or exploration sequences.
Each step is a dict with action type and parameters.

### Key Methods

| Method | Description |
|--------|-------------|
| `load_waypoint_file(file)` | Parse waypoint JSON, validate steps |
| `step()` | Current step dict |
| `next_step()` | Advance to next step |
| `reset()` | Restart from step 0 |
| `log_stats()` | Print route progress/timing |

### Station Services

EDWayPoint orchestrates station interactions (buy/sell commodities, refuel)
by calling into `EDStationServicesInShip` and reading `CargoParser`/`MarketParser`.

### Dependencies

- `src.ed.CargoParser` -- read cargo inventory
- `src.ed.MarketParser` -- read station market
- `src.ed.EDJournal` -- StationType enum
- `src.core.EDAP_data` -- flag constants
- Accesses `ap.ship.cargo_capacity` for trade calculations
