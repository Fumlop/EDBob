# EDShipControl.py

## Purpose
Basic ship control interface for managing GUI focus states. Primarily handles returning to cockpit view by closing any open panels.

## Key Classes/Functions
- EDShipControl: Handles ship control and panel state management

## Key Methods
- goto_cockpit_view(): Delegates to `MenuNav.goto_cockpit()`. Returns True when in cockpit view.

## Dependencies
- MenuNav: All menu key sequences delegated here
- StatusParser: Monitors GUI focus state (GuiFocusNoFocus constant)
- EDAP_data: Global constants for GUI focus states

## Notes
- Thin wrapper, actual key logic lives in MenuNav
- Can be extended for additional ship control operations
