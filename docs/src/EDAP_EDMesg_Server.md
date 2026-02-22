# EDAP_EDMesg_Server.py -- EDMesg Server

## Purpose

EDMesg server that allows external clients (e.g. EDCoPilot) to connect to EDAP and send actions or receive events via the EDMesg protocol.
Lives in `src/autopilot/EDAP_EDMesg_Server.py`.

## Class: EDMesgServer

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `cb` | callable | GUI callback |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Parent reference |
| `ap_ckb` | callable | GUI callback |
| `actions_port` | int | ZMQ port for incoming actions (0 = auto) |
| `events_port` | int | ZMQ port for outgoing events (0 = auto) |
| `_provider` | EDMesgProvider or None | EDMesg provider instance |
| `_server_loop_thread` | Thread or None | Background server loop thread |

### Methods

| Method | Returns | Description |
|---|---|---|
| `start_server()` | None | Creates EDMesg provider via `create_edap_provider()`, starts `_server_loop` on daemon thread. Logs error on failure. |
| `_server_loop()` | None | Background loop: polls `pending_actions` queue every 0.1s, dispatches to handler methods by action type. Closes provider on exit. |
| `_get_edap_location(provider)` | None | Handles `GetEDAPLocationAction`: publishes `EDAPLocationEvent` with EDAP install path. |
| `_load_waypoint_file(filepath)` | None | Handles `LoadWaypointFileAction`: calls `ap.waypoint.load_waypoint_file()`. |
| `_start_waypoint_assist()` | None | Handles `StartWaypointAssistAction`: triggers via `ap_ckb('waypoint_start')`. |
| `_stop_all_assists()` | None | Handles `StopAllAssistsAction`: triggers via `ap_ckb('stop_all_assists')`. |
| `_launch(provider)` | None | Handles `LaunchAction`: publishes `LaunchCompleteEvent` after 1s delay. |
| `_system_map_target_station_by_bookmark(bm_type, number)` | None | Handles `SystemMapTargetStationByBookmarkAction`: opens system map and sets bookmark destination. |
| `_galaxy_map_target_station_by_bookmark(bm_type, number)` | None | Handles `GalaxyMapTargetStationByBookmarkAction`: opens galaxy map and sets bookmark destination. |
| `_galaxy_map_target_system_by_name(name)` | None | Handles `GalaxyMapTargetSystemByNameAction`: opens galaxy map and searches by system name. |
| `_generic_action(name)` | None | Handles `GenericAction`: logs the action name. |

### Action Dispatch Table

| Action Class | Handler |
|---|---|
| `EDMesgWelcomeAction` | Log only |
| `GetEDAPLocationAction` | `_get_edap_location` |
| `LoadWaypointFileAction` | `_load_waypoint_file` |
| `StartWaypointAssistAction` | `_start_waypoint_assist` |
| `StopAllAssistsAction` | `_stop_all_assists` |
| `LaunchAction` | `_launch` |
| `SystemMapTargetStationByBookmarkAction` | `_system_map_target_station_by_bookmark` |
| `GalaxyMapTargetStationByBookmarkAction` | `_galaxy_map_target_station_by_bookmark` |
| `GalaxyMapTargetSystemByNameAction` | `_galaxy_map_target_system_by_name` |
| `GenericAction` | `_generic_action` |

## Module-Level Functions

| Function | Description |
|---|---|
| `main()` | Test harness: creates EDMesgServer with None params. |

## Dependencies

| Module | Purpose |
|---|---|
| `EDAP_EDMesg_Interface` | Action/event classes and `create_edap_provider()` factory |
| `EDMesg.EDMesgBase` | `EDMesgWelcomeAction` base class |
| `EDlogger` | Logging |

## Notes

- Server runs on a daemon thread; dies with main process
- Uses `isinstance()` chain for action dispatch (not a dict mapping)
- `_launch` handler is a stub -- waypoint undock is commented out
- All actions are logged to GUI callback before processing
- Provider is closed in `finally` block on server loop exit
