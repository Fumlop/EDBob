# EDKeys.py

## Purpose
Reads Elite Dangerous keybindings from .binds XML files and provides methods to send keyboard input to the game with configurable key presses, modifiers, and timings.

## Key Classes/Functions

### EDKeys
- Main class for keybinding management and keyboard input simulation

## Key Methods

- `__init__(cb)`: Initialize with callback function, load keybindings from latest .binds file
- `get_bindings()`: Parse .binds XML file and return direct input key equivalents with modifiers
- `get_bindings_dict()`: Returns raw dictionary of all ED keybindings from XML
- `get_latest_keybinds()`: Finds most recently modified .binds file in ED options directory
- `send(key_binding, hold, repeat, repeat_delay, state)`: Send keyboard input based on keybinding name
  - `hold`: Duration to hold key (seconds)
  - `repeat`: Number of times to repeat press
  - `state`: None (press+release), 1 (press only), 0 (release only)
- `send_key(type, key)`: Low-level key send (Up/Down)
- `check_hotkey_in_bindings(key_name)`: Check if hotkey is used in ED bindings
- `get_collisions(key_name)`: Find keys bound to multiple actions
- `get_collisions(key_name)`: Find keys bound to multiple actions

## Dependencies

- xml.etree, win32gui
- xmltodict
- directinput
- EDlogger, Screen

## Notes

- Monitors 37 commonly used ED keybindings (yaw, pitch, roll, speed, UI navigation, weapons, etc.)
- Validates against ED hotkeys (End, Insert, PageUp, Home) and warns if conflicts exist
- Key delays configurable: `key_mod_delay` (0.01s), `key_def_hold_time` (0.2s), `key_repeat_delay` (0.1s)
- Reads from %LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Bindings
- Supports primary and secondary keybindings from XML, prefers secondary
- Logs missing keys and collision warnings to callback
