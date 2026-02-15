# EDlogger.py

## Purpose
Centralized logging configuration for the application. Sets up file and console logging with color support, manages log file rotation, and provides global logger instance.

## Key Classes/Functions
- logger: Global colorlog instance configured for application-wide use

## Logging Configuration
- File logging: autopilot.log with ERROR level (all messages)
- Console logging: WARNING level with color formatting
- Log format: "HH:MM:SS.mmm LEVEL MESSAGE"
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Log File Management
- Automatic rotation of existing logs (timestamp appended)
- Example: autopilot.log -> autopilot 2025-02-15 10-30-45.log
- New autopilot.log created on each run

## Color Scheme
- DEBUG: Bold cyan
- INFO: Bold green
- WARNING: Bold blue on bold yellow background
- ERROR: Bold white on bold red background
- CRITICAL: Bold yellow on bold red background

## Dependencies
- logging: Python standard logging module
- colorlog: Color formatting for console output
- datetime: Timestamp generation for log rotation
- pathlib.Path: Path manipulation

## Usage
```python
from EDlogger import logger
logger.info("Message")
logger.debug("Debug info")
logger.warning("Warning")
logger.error("Error")
```

## Notes
- Logger instance created at module load time
- Python version logged on initialization
- File logging captures all output; console selective by level
- Can be disabled with logger.disabled = True/False
- Initial logger level set to INFO (change to DEBUG for verbose output)
