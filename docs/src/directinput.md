# directinput.py

## Purpose
Low-level Windows DirectInput keyboard simulation using ctypes. Provides DirectInput scan code definitions and functions to press/release keys via Windows SendInput API.

## Key Classes/Functions
- KeyBdInput: ctypes structure for keyboard input
- HardwareInput: ctypes structure for hardware input
- MouseInput: ctypes structure for mouse input
- Input_I: ctypes union combining all input types
- Input: ctypes structure wrapping input type and data

## Key Methods
- PressKey(hexKeyCode): Sends key press event to Windows
- ReleaseKey(hexKeyCode): Sends key release event to Windows

## SCANCODE Dictionary
Comprehensive mapping of 254 DirectInput scan codes to named constants:
- Function keys: Key_F1 through Key_F12
- Letters: Key_A through Key_Z
- Numbers: Key_0 through Key_9
- Navigation: Arrow keys, PageUp, PageDown, Home, End, Insert, Delete
- Media: Play/Pause, Next/Prev Track, Mute, Volume controls
- Modifiers: LeftControl, RightControl, LeftShift, RightShift, LeftAlt, RightAlt
- Special: Space, Enter, Tab, Escape, NumLock, etc.

## Dependencies
- ctypes: Windows API bindings
- time: Module for timing (imported but not used in core functions)

## Notes
- Uses DirectInput scan codes (0x0008 flag for KEYBD_EVENT_SCANCODE)
- Key release uses 0x0002 flag (KEYEVENT_KEYUP)
- Direct Windows API integration bypassing keyboard library abstractions
- Suitable for game input where standard input methods fail
