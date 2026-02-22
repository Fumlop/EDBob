# EDlogger.py -- Logging Configuration

## Purpose

Configures the application-wide logger with file rotation, colored console output, and log level management. Creates a single `logger` instance used throughout the codebase.
Lives in `src/core/EDlogger.py`.

## Module-Level Setup (runs on import)

1. **Startup rotation**: If `autopilot.log` exists, shifts existing logs: `.4` -> `.5`, `.3` -> `.4`, ... `.1` -> `.2`, `log` -> `.1`. Max 5 backups.
2. **File handler**: `RotatingFileHandler` on `autopilot.log`, 10 MB max, no additional rotation (rotation handled at startup), UTF-8 encoding.
3. **Console handler**: `colorlog.ColoredFormatter` with color-coded levels:
   - DEBUG: cyan
   - INFO: green
   - WARNING: yellow bg, blue text
   - ERROR: red bg, white text
   - CRITICAL: red bg, yellow text
4. **Default levels**: File = INFO, Console = WARNING

## Exported Symbols

| Symbol | Type | Description |
|---|---|---|
| `logger` | `colorlog.Logger` | Application-wide logger instance named `'ed_log'` |

## Log Format

- File: `HH:MM:SS.mmm LEVEL    message`
- Console: Color-coded level + white message

## Configuration Constants

| Constant | Value | Description |
|---|---|---|
| `_filename` | `'autopilot.log'` | Log file name |
| `_max_backups` | 5 | Maximum rotated backup files |

## Dependencies

| Module | Purpose |
|---|---|
| `colorlog` | Colored console output |
| `logging` | Standard logging framework |
| `logging.handlers.RotatingFileHandler` | File rotation by size |

## Notes

- Log file rotation happens at application startup (not by size during runtime, despite using RotatingFileHandler)
- `backupCount=0` on RotatingFileHandler means no size-based rotation -- only the startup rotation applies
- `maxBytes=10_000_000` (10 MB) limit exists but with `backupCount=0` the file just gets truncated
- Logger level can be changed at runtime via `ED_AP.set_log_*()` methods
- Logs Python version at startup (INFO level)
