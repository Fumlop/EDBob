# WindowsKnownPaths.py

## Purpose
Windows Shell API wrapper for resolving known folder paths. Provides cross-platform path resolution for system directories like Documents, Downloads, SavedGames, etc.

## Key Classes/Functions
- GUID: ctypes Structure mapping UUID to Windows GUID format
- FOLDERID: Class with 100+ UUID constants for Windows known folder IDs
- UserHandle: Enum-like class for user context (current/common)
- PathNotFoundException: Exception raised when folder not found

## Key Methods
- get_path(folderid, user_handle=UserHandle.common): Resolves full path for given folder ID, returns string path

## FOLDERID Constants (Sample)
- Desktop, Documents, Downloads, Pictures, Videos
- SavedGames: For Elite Dangerous game data files
- LocalAppData: For game configuration files
- ProgramFiles, System, Windows
- Music, Contacts, Favorites, History, Recent
- CommonAdminTools, CommonPrograms, CommonStartMenu

## Dependencies
- ctypes: Windows API bindings (windll, wintypes)
- uuid: UUID handling for FOLDERID constants
- sys: Used in __main__ for CLI argument handling

## Usage
```python
from WindowsKnownPaths import get_path, FOLDERID, UserHandle
saved_games = get_path(FOLDERID.SavedGames, UserHandle.current)
```

## Command Line Usage
```
python WindowsKnownPaths.py SavedGames current
python WindowsKnownPaths.py Documents
```

## Notes
- Uses Windows Shell32 API (SHGetKnownFolderPath)
- Automatic COM memory cleanup (CoTaskMemFree)
- Currently Windows-only (ctypes/windll Windows-specific)
- UserHandle.current = current user, UserHandle.common = all users
- Used by CargoParser, MarketParser for finding Elite Dangerous game files
