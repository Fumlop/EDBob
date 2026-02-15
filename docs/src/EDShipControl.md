# EDShipControl.py

## Purpose
Basic ship control interface for managing GUI focus states. Primarily handles returning to cockpit view by closing any open panels.

## Key Classes/Functions
- EDShipControl: Handles ship control and panel state management

## Key Methods
- goto_cockpit_view(): Returns to cockpit view by sending UI_Back commands until all panels are closed, returns True when complete

## Dependencies
- StatusParser: Monitors GUI focus state (GuiFocusNoFocus constant)
- EDAP_data: Global constants for GUI focus states

## Notes
- Simple implementation currently focused on panel management
- Uses StatusParser to check current GUI focus state
- Can be extended for additional ship control operations
