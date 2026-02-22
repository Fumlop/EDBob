# WindowsKnownPaths.py -- Windows Known Folder Paths

## Purpose

Wraps the Windows Shell API `SHGetKnownFolderPath` to resolve known folder paths (Documents, SavedGames, etc.). Used throughout the codebase to find Elite Dangerous data files.
Lives in `src/core/WindowsKnownPaths.py`.

## Classes

### GUID

ctypes Structure wrapping a Windows GUID from a Python `UUID`.

| Method | Description |
|---|---|
| `__init__(uuid_)` | Parse UUID fields into DWORD/WORD/BYTE structure. |

### FOLDERID

Collection of `UUID` constants for Windows known folders. Key entries used by this project:

| Attribute | Description |
|---|---|
| `SavedGames` | `{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}` -- used to find `Status.json`, `NavRoute.json`, `Cargo.json`, `Market.json` |
| `LocalAppData` | `{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}` |
| `Documents` | `{FDD39AD0-238F-46AF-ADB4-6C85480369C7}` |
| `Desktop` | `{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}` |

Contains 110+ known folder IDs covering all standard Windows locations.

### UserHandle

| Attribute | Type | Description |
|---|---|---|
| `current` | HANDLE(0) | Current user |
| `common` | HANDLE(-1) | All users (common/public) |

### PathNotFoundException

Exception raised when `SHGetKnownFolderPath` fails.

## Functions

| Function | Returns | Description |
|---|---|---|
| `get_path(folderid, user_handle=UserHandle.common)` | str | Resolve a known folder path. Calls `SHGetKnownFolderPath`, frees COM memory with `CoTaskMemFree`. Raises `PathNotFoundException` on failure. |

## Usage Pattern

```python
from src.core.WindowsKnownPaths import get_path, FOLDERID, UserHandle
saved_games = get_path(FOLDERID.SavedGames, UserHandle.current)
# -> "C:\Users\<user>\Saved Games"
status_path = saved_games + "/Frontier Developments/Elite Dangerous/Status.json"
```

## Dependencies

| Module | Purpose |
|---|---|
| `ctypes` / `windll` / `wintypes` | Windows API access |
| `uuid.UUID` | Python UUID for GUID conversion |

## Notes

- Windows-only module (uses `shell32.SHGetKnownFolderPath`)
- Primary use: resolving `SavedGames` folder for ED journal/status files
- `UserHandle.current` is used for per-user paths, `UserHandle.common` for shared paths
- Standalone `__main__` block accepts folder name and user handle as CLI arguments
- COM memory is properly freed via `CoTaskMemFree`
