# EDGraphicsSettings.py -- Graphics Settings Reader

## Purpose

Reads Elite Dangerous graphics XML settings files (`DisplaySettings.xml` and `Settings.xml`) to extract screen resolution, fullscreen mode, monitor, and FOV. Validates display mode (rejects Fullscreen, warns on Windowed).
Lives in `src/ed/EDGraphicsSettings.py`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `main()` | None | Test harness, creates `EDGraphicsSettings` instance. |

## Class: EDGraphicsSettings

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `display_file_path` | str or None | Custom path to DisplaySettings.xml. Default: `%LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Graphics\DisplaySettings.xml` |
| `settings_file_path` | str or None | Custom path to Settings.xml. Default: `%LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Graphics\Settings.xml` |

### Constructor Behavior

1. Validates both files exist (raises Exception if not)
2. Reads and parses both XML files via `xmltodict`
3. Extracts `ScreenWidth`, `ScreenHeight`, `FullScreen`, `Monitor` from DisplaySettings
4. Maps FullScreen value: 0=Windowed, 1=Fullscreen, 2=Borderless
5. Raises Exception if Fullscreen mode (overlay cannot work)
6. Warns if Windowed mode (Borderless recommended)
7. Extracts `FOV` from Settings

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `fullscreen` | str | Raw fullscreen value (0/1/2) |
| `fullscreen_str` | str | Human-readable: "Windowed", "Fullscreen", or "Borderless" |
| `screenwidth` | str | Screen width from DisplaySettings |
| `screenheight` | str | Screen height from DisplaySettings |
| `monitor` | str | Monitor identifier |
| `fov` | str | Field of view from Settings |
| `display_settings_filepath` | str | Path to DisplaySettings.xml |
| `settings_filepath` | str | Path to Settings.xml |
| `display_settings` | dict | Parsed DisplaySettings XML |
| `settings` | dict | Parsed Settings XML |

### Methods

| Method | Returns | Description |
|---|---|---|
| `read_settings(filename)` | dict | Static. Reads XML file, parses with `xmltodict.parse()`, returns dict. Raises Exception on OS error. |

## Dependencies

| Module | Purpose |
|---|---|
| `xmltodict` | XML to dict parsing |
| `EDlogger` | Logging |
| `os.environ` | `LOCALAPPDATA` for default file paths |

## Notes

- Fullscreen mode is rejected because screen overlay cannot work over exclusive fullscreen
- Borderless mode is recommended; Windowed mode works but may have issues
- All extracted values are strings (not converted to int/float)
- Constructor is the main entry point -- all reading and validation happens there
