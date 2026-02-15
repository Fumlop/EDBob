# Robigo.py

## Purpose
Automated mission running script for the Robigo passenger mission loop. Manages mission selection at Sothis station, travel to Robigo Mines, and return cycles with state machine logic.

## Key Classes/Functions
- Robigo: State machine implementation for Robigo mission loop automation

## Key Methods
- determine_state(ap): Returns current state based on ship location, status, and target
- get_missions(ap): Selects Sirius Atmospherics missions from mission board
- complete_missions(ap): Turns in completed missions for credit
- goto_passenger_lounge(ap): Navigates from docked position to passenger lounge menu
- lock_target(ap, templ): Uses image template matching to find and select target in nav panel
- select_mission(ap): Completes mission selection with auto-fill cabin assignment
- travel_to_sirius_atmos(ap): Supercruises to Sirius Atmospherics, waits for mission redirection
- loop(ap): Main mission loop orchestrating all states

## State Constants
- STATE_MISSIONS: Mission turn-in and selection
- STATE_ROUTE_TO_SOTHIS: Galaxy map routing
- STATE_UNDOCK: Station undocking
- STATE_FSD_TO_SOTHIS: FSD jump to Sothis
- STATE_TARGET_SIRIUS: Nav panel target selection
- STATE_SC_TO_SIRIUS: Supercruise travel
- STATE_ROUTE_TO_ROBIGO: Return routing
- STATE_FSD_TO_ROBIGO: FSD return jump
- STATE_TARGET_ROBIGO_MINES: Robigo Mines target selection
- STATE_SC_TO_ROBIGO_MINES: Final approach and docking

## Dependencies
- ED_AP: Autopilot engine with routing and navigation
- EDJournal: Ship state and mission tracking
- Image_Templates: Template matching for nav panel items

## Notes
- Odyssey-only (different mission menus vs Horizon)
- Requires nav filter set to "Stations and POI" for cleaner list
- Station layout and menu positions critical for reliability
- Image template matching used for location identification
- Can run single loop or continuous mission cycles
