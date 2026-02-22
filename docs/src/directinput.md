# directinput.py -- DirectInput Key Simulation

## Purpose

Low-level keyboard input simulation using Windows `SendInput` API with DirectInput scan codes. Provides press/release functions for game input that bypasses normal Windows keyboard handling.
Lives in `src/core/directinput.py`.

## Scan Code Dictionary

`SCANCODE` maps string key names to DirectInput scan code integers (0-254). Notable entries:

| Key Name | Code | Description |
|---|---|---|
| `Key_Escape` | 1 | Escape |
| `Key_1` through `Key_0` | 2-11 | Number row |
| `Key_Q` through `Key_P` | 16-25 | Top letter row |
| `Key_A` through `Key_L` | 30-38 | Home letter row |
| `Key_Z` through `Key_M` | 44-50 | Bottom letter row |
| `Key_Space` | 57 | Space bar |
| `Key_F1` through `Key_F12` | 59-68, 87-88 | Function keys |
| `Key_Numpad_*` | 71-83, 156, 181 | Numpad keys |
| `Key_UpArrow` | 200 | Up arrow |
| `Key_DownArrow` | 208 | Down arrow |
| `Key_LeftArrow` | 203 | Left arrow |
| `Key_RightArrow` | 205 | Right arrow |
| `Key_Home` / `Key_End` | 199 / 207 | Home/End |
| `Key_PageUp` / `Key_PageDown` | 201 / 209 | Page Up/Down |
| `Key_Insert` / `Key_Delete` | 210 / 211 | Insert/Delete |
| `Key_LeftControl` / `Key_RightControl` | 29 / 157 | Control keys |
| `Key_LeftAlt` / `Key_RightAlt` | 56 / 184 | Alt keys |
| `Key_LeftShift` / `Key_RightShift` | 42 / 54 | Shift keys |

Unknown/reserved codes are prefixed with `??_`.

## C Struct Definitions

| Class | Description |
|---|---|
| `KeyBdInput` | Keyboard input structure: `wVk`, `wScan`, `dwFlags`, `time`, `dwExtraInfo` |
| `HardwareInput` | Hardware input structure (unused) |
| `MouseInput` | Mouse input structure (unused) |
| `Input_I` | Union of keyboard, mouse, hardware input |
| `Input` | Top-level input structure: `type` + `Input_I` union |

## Extended Key Handling

`_EXTENDED_SCANCODES` set contains scan codes that require `KEYEVENTF_EXTENDEDKEY` flag:
- Numpad Enter (156), Right Control (157), Numpad Divide (181)
- Right Alt (184), Pause (197)
- Arrow keys (200, 203, 205, 208)
- Home (199), End (207), Page Up/Down (201, 209)
- Insert (210), Delete (211), Apps (221)

## Functions

| Function | Description |
|---|---|
| `_is_extended_key(hexKeyCode)` | Returns True if scan code needs `KEYEVENTF_EXTENDEDKEY` flag. |
| `PressKey(hexKeyCode)` | Send key-down event via `SendInput`. Uses `KEYEVENTF_SCANCODE`, adds `KEYEVENTF_EXTENDEDKEY` for extended keys. |
| `ReleaseKey(hexKeyCode)` | Send key-up event via `SendInput`. Uses `KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP`, adds `KEYEVENTF_EXTENDEDKEY` for extended keys. |

## Dependencies

| Module | Purpose |
|---|---|
| `ctypes` | Windows API access (`windll.user32.SendInput`) |
| `time` | Imported but not used directly in this file |

## Notes

- Uses scan codes (not virtual key codes) for DirectInput compatibility with games
- Extended key flag is critical for arrow keys, numpad enter, right-side modifier keys
- `PressKey` and `ReleaseKey` are the only public API -- callers must handle timing/hold between press and release
- Higher-level key sending with hold/repeat logic is in `EDKeys` class
