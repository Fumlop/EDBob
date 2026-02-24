# src/ed/StatusParser.py (409 lines)

Real-time game status from `status.json`. The game overwrites this file every ~1s
with current flags, pips, fuel, gui focus, and position.

## Class: StatusParser

### Key Methods

| Method | Description |
|--------|-------------|
| `get_flag(flag)` | Check a single flag bit (e.g. `FlagsSupercruise`) |
| `get_gui_focus()` | Current GUI focus (0=flying, 6=galaxy map, etc.) |
| `wait_for_file_change(ts, timeout)` | Block until status.json mod time changes |
| `get_cleaned_data()` | Full parsed status dict |

### Read Strategy

Reads the file on every call (mod-time check first). The file is tiny (~200 bytes)
and polling is cheap. No threading needed -- different beast from journal.

### Notes

- Status.json is not append-only (overwritten in place)
- 31 reads per engine loop iteration is fine (mod-time cache)
- Ship.update_flight_mode() uses status parser to detect SC vs normal

## Dependencies

- `src.core.EDAP_data` -- flag constants
- `src.core.WindowsKnownPaths` -- savegames path
