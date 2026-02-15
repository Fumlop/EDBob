# MousePt.py

## Purpose
Mouse position tracking and clicking utility. Captures mouse click coordinates and executes mouse clicks at specified screen positions.

## Key Classes/Functions
- MousePoint: Handles mouse event listening and click execution

## Key Methods
- get_location(): Starts mouse listener, blocks until user clicks, returns (x, y) tuple
- do_click(x, y, delay=0.1): Moves mouse to position and executes left click with configurable hold time
- on_click(x, y, button, pressed): Callback for mouse click events (stores position, sets termination flag)
- on_move(x, y): Callback for mouse move events (placeholder)
- on_scroll(x, y, dx, dy): Callback for scroll events (placeholder)

## Attributes
- x, y: Current mouse position
- term: Termination flag for blocking listener loop
- ls: Mouse listener instance
- ms: Mouse controller instance

## Dependencies
- pynput.mouse: Cross-platform mouse control and listening
- time.sleep: Sleep for polling loop

## Notes
- Uses pynput for cross-platform mouse control
- get_location() blocks main thread until click detected
- do_click() includes small delay between press and release
- Listener started/stopped on demand (not persistent)
- Initial example in main() shows clicking at position (1977, 510)
