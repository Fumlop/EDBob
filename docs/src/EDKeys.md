# src/ed/EDKeys.py (402 lines)

Key binding loader and DirectInput key sender.

## Class: EDKeys

Reads Elite Dangerous `.binds` XML files to map logical key names
(e.g. `PitchUpButton`) to DirectInput scan codes. Sends keystrokes
to the ED window via `SendInput`.

### Key Methods

| Method | Description |
|--------|-------------|
| `send(key_name, hold, repeat)` | Send a key with optional hold time and repeat |
| `load_bindings()` | Parse *.binds XML for key mappings |

### Binding Resolution

Reads from `%LOCALAPPDATA%\Frontier Developments\Elite Dangerous\Options\Bindings\`.
Supports primary and secondary bindings. Modifier keys supported.

### Key Names Used by Ship

```
PitchUpButton, PitchDownButton
RollRightButton, RollLeftButton
YawRightButton, YawLeftButton
SetSpeedZero, SetSpeed25, SetSpeed50, SetSpeed100
UseBoostJuice, HyperSuperCombination
```

## Dependencies

- `src.core.directinput` -- SCANCODE map, SendInput
- `src.screen.Screen` -- focus checking
- `src.core.WindowsKnownPaths` -- bindings path
