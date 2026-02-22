# EDKeys.py -- Keybinding Manager

## Purpose

Reads Elite Dangerous keybindings from `.binds` XML files and provides methods to send
keyboard input to the game. Parses the latest modified `.binds` file, maps ED key names
to DirectInput scancodes, handles modifier keys and hold timing, and validates for
missing or conflicting bindings.
Lives in `src/ed/EDKeys.py`. Marked `@final` -- not intended for subclassing.

## Architecture

- Single `EDKeys` class, instantiated once by the autopilot
- Reads `.binds` XML from `%LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Bindings`
- Prefers secondary keybinding over primary when both are keyboard-bound
- Hardcoded fallback keys for common defaults when a binding is missing
- Callback system (`ap_ckb`) for GUI warnings about missing/colliding keys
- Focus check throttled to every 5 seconds to avoid disrupting key holds

## Module-Level Constants

None (all configuration is instance-level).

## EDKeys Class

### Instance Attributes

| Attribute | Type | Default | Description |
|---|---|---|---|
| `ap_ckb` | callable | (from init) | Callback for GUI logging |
| `key_mod_delay` | `float` | 0.01 | Delay in seconds for modifier keys before/after main key |
| `key_def_hold_time` | `float` | 0.2 | Default hold time for a key press in seconds |
| `key_repeat_delay` | `float` | 0.1 | Delay in seconds between key press repeats |
| `activate_window` | `bool` | True | Whether to focus Elite window before sending keys |
| `_last_focus_check` | `float` | 0 | Timestamp of last window focus check |
| `keys_to_obtain` | `list[str]` | (see below) | List of ED binding names to extract from .binds file |
| `_fallback_keys` | `dict` | (see below) | Hardcoded fallback scancodes for missing bindings |
| `keys` | `dict` | (from get_bindings) | Parsed keybindings: `{name: {key: scancode, mods: [scancodes], hold?: bool}}` |
| `bindings` | `dict` | (from get_bindings_dict) | Raw XML-to-dict of all ED keybindings |
| `missing_keys` | `list[str]` | [] | List of binding names that could not be resolved |
| `reversed_dict` | `dict` | (computed) | Reverse map of scancode to key name for logging |

### Keybindings Tracked (`keys_to_obtain`)

| Category | Bindings |
|---|---|
| Flight | `YawLeftButton`, `YawRightButton`, `RollLeftButton`, `RollRightButton`, `PitchUpButton`, `PitchDownButton`, `SetSpeedZero`, `SetSpeed25`, `SetSpeed50`, `SetSpeed75`, `SetSpeed100`, `UpThrustButton`, `UseBoostJuice`, `LandingGearToggle` |
| Navigation | `HyperSuperCombination`, `Supercruise`, `SelectTarget`, `TargetNextRouteSystem`, `GalaxyMapOpen`, `SystemMapOpen` |
| UI | `FocusLeftPanel`, `UIFocus`, `UI_Up`, `UI_Down`, `UI_Left`, `UI_Right`, `UI_Select`, `UI_Back`, `CycleNextPanel`, `CyclePreviousPanel`, `HeadLookReset` |
| Power | `IncreaseEnginesPower`, `IncreaseWeaponsPower`, `IncreaseSystemsPower` |
| Combat | `DeployHeatSink`, `DeployHardpointToggle`, `PrimaryFire`, `SecondaryFire` |
| Exploration | `ExplorationFSSEnter`, `ExplorationFSSQuit`, `MouseReset`, `CamZoomIn`, `CamTranslateForward`, `CamTranslateRight`, `OrderAggressiveBehaviour` |

### Fallback Keys

When a binding is missing from the `.binds` file, these defaults are used:

| Binding | Default Key |
|---|---|
| `YawLeftButton` | Numpad 4 |
| `YawRightButton` | Numpad 6 |
| `RollLeftButton` | A |
| `RollRightButton` | D |
| `PitchUpButton` | Numpad 8 |
| `PitchDownButton` | Numpad 2 |
| `SetSpeedZero` | Left Shift |
| `SetSpeed50` | Y |
| `SetSpeed100` | C |
| `UpThrustButton` | R |
| `UseBoostJuice` | Tab |
| `LandingGearToggle` | L |
| `HyperSuperCombination` | J |
| `Supercruise` | Numpad + |
| `SelectTarget` | T |
| `TargetNextRouteSystem` | K |
| `GalaxyMapOpen` | Page Up |
| `SystemMapOpen` | Page Down |
| `FocusLeftPanel` | 1 |
| `UIFocus` | 5 |
| `UI_Up` | W |
| `UI_Down` | S |
| `UI_Left` | A |
| `UI_Right` | D |
| `UI_Select` | Space |
| `UI_Back` | Backspace |
| `CycleNextPanel` | E |
| `CyclePreviousPanel` | Q |
| `HeadLookReset` | 7 |
| `IncreaseEnginesPower` | Up Arrow |
| `IncreaseWeaponsPower` | Right Arrow |
| `IncreaseSystemsPower` | Left Arrow |
| `DeployHardpointToggle` | U |

### Methods

| Method | Returns | Description |
|---|---|---|
| `__init__(cb)` | None | Init with callback. Loads keybindings from latest `.binds` file, applies fallbacks for missing keys, logs all resolved bindings, warns on missing keys and collisions, checks EDAP hotkeys (End, Insert, PageUp, Home) against ED bindings. |
| `get_bindings()` | `dict[str, Any]` | Parse `.binds` XML file via `xml.etree.ElementTree`. For each binding in `keys_to_obtain`, extracts primary and secondary keyboard keys with modifiers. Secondary preferred over primary. Returns dict of `{name: {key: scancode, mods: [scancodes], hold?: bool}}`. Returns empty dict if no bindings found. |
| `get_bindings_dict()` | `dict[str, Any]` | Parse `.binds` XML file via `xmltodict` into a raw nested dict. Returns the full bindings structure with Primary/Secondary entries per binding. Used for collision and hotkey checks. |
| `check_hotkey_in_bindings(key_name)` | `str` | Check if a key name (e.g. 'Key_End') is used in any ED binding. Returns a string of matching binding names joined by " and " (e.g. "GalaxyMapOpen (Primary) and SystemMapOpen (Secondary)"). Returns empty string if no matches. |
| `get_latest_keybinds()` | `str` or None | Find the most recently modified `.binds` file in `%LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Bindings`. Returns full path or None if directory/files not found. |
| `send_key(type, key)` | None | Low-level key send. `type='Up'` releases key, anything else presses key. Delegates to `directinput.PressKey`/`ReleaseKey`. |
| `has_binding(key_binding)` | `bool` | Check if a keybinding name exists in the resolved keys dict. |
| `send(key_binding, hold, repeat, repeat_delay, state)` | None | Send a key based on the defined keybind. Handles modifier keys, hold timing, repeat count, and press/release states. Focuses Elite window before sending (throttled to every 5s). Raises Exception if binding not found. |
| `get_collisions(key_name)` | `list[str]` | Find all binding names that share the same key+mods as the given binding. Returns list of colliding binding names (includes the queried binding itself). |

### `send()` Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `key_binding` | `str` | (required) | Binding name (e.g. 'UseBoostJuice') |
| `hold` | `float` or None | None | Time to hold key in seconds. If None, uses `key_def_hold_time` (0.2s). |
| `repeat` | `int` | 1 | Number of times to repeat the key press |
| `repeat_delay` | `float` or None | None | Delay between repeats in seconds. If None, uses `key_repeat_delay` (0.1s). |
| `state` | `int` or None | None | Key state: None = press and release, 1 = press only, 0 = release only |

### `send()` Key Sequence

```
For each repeat:
  1. If state is None or 1:
     a. Press each modifier key (with key_mod_delay between)
     b. Press main key
  2. If state is None:
     a. Sleep for hold time (or key_def_hold_time if hold not specified)
  3. If binding has 'hold' flag: additional 0.1s sleep
  4. If state is None or 0:
     a. Release main key
     b. Release each modifier key (with key_mod_delay between)
  5. Sleep for repeat_delay (or key_repeat_delay)
```

### Init Validation

During `__init__`, the following checks are performed:

1. All bindings in `keys_to_obtain` are logged with their resolved key names
2. Bindings that failed to resolve (not in `.binds` and not in fallbacks) are added to `missing_keys` and warned via callback
3. Each resolved binding is checked for collisions (same key+mods used by multiple bindings) and warned via callback
4. EDAP hotkeys (`Key_End`, `Key_Insert`, `Key_PageUp`, `Key_Home`) are checked against all ED bindings and warned if conflicts found

## Dependencies

| Module | Purpose |
|---|---|
| `directinput` | `SCANCODE` dict for key name to scancode mapping, `PressKey`/`ReleaseKey` for input simulation |
| `EDlogger` | Logging via `logger` |
| `Screen` | `set_focus_elite_window()` for window focus before key sends |
| `xmltodict` | XML-to-dict conversion for full bindings parsing |
| `xml.etree.ElementTree` | XML parsing for selective keybinding extraction |
| `win32gui` | (imported, used indirectly via Screen) |
| `json` | JSON serialization for warning messages |

## Notes

- The class is marked `@final` and should not be subclassed
- Secondary keybindings are preferred over primary (secondary overwrites primary if both are keyboard)
- The `hold` flag in a binding comes from the `<Hold>` element in the `.binds` XML, adding an extra 0.1s delay
- Window focus is checked at most every 5 seconds to avoid disrupting held keys
- Fallback keys only apply to missing bindings, not to bindings that resolve to non-keyboard devices
- 37 bindings are tracked across 6 categories (flight, navigation, UI, power, combat, exploration)
