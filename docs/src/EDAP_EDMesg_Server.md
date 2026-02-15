# EDAP_EDMesg_Server.md

## Purpose
Implements server-side EDMesg provider that listens for client actions and dispatches them to EDAP autopilot functions, sending events back to clients.

## Key Classes/Functions
- EDMesgServer: Main server that manages provider and action handling loop

## Key Methods
- __init__(ed_ap, cb): Initializes with EDAP autopilot reference and callback function
- start_server(): Creates EDMesgProvider and starts background server loop
- _server_loop(): Daemon thread polling for actions and dispatching handlers
- _get_edap_location(provider): Returns EDAP installation path to client
- _load_waypoint_file(filepath): Loads waypoint file through autopilot
- _start_waypoint_assist(): Initiates waypoint navigation via callback
- _stop_all_assists(): Cancels all assists via callback
- _launch(provider): Triggers launch and publishes LaunchCompleteEvent
- _system_map_target_station_by_bookmark(bm_type, number): Sets system map destination
- _galaxy_map_target_station_by_bookmark(bm_type, number): Sets galaxy map destination
- _galaxy_map_target_system_by_name(name): Sets galaxy map destination by name
- _generic_action(name): Handles generic named actions (e.g., WriteTCEShoppingList)

## Dependencies
- threading: Background server loop
- EDAP_EDMesg_Interface: Factory and all action/event types
- EDMesg.EDMesgBase: EDMesgWelcomeAction for client detection

## Notes
- Server ports initialized to 0 (must be set before start_server)
- All autopilot operations routed through callback or direct ed_ap reference
- Logging via callback allows integration with main application
- Exception handling is basic (bare except)
- TCE integration support for shopping list operations
