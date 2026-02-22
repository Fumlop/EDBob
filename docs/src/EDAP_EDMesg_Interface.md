# EDAP_EDMesg_Interface.py -- EDMesg Protocol Definitions

## Purpose

Defines the EDMesg action and event types for the EDAP provider, plus factory methods to create provider and client instances. This is the protocol contract between EDAP and external EDMesg clients.
Lives in `src/autopilot/EDAP_EDMesg_Interface.py`.

## Action Classes (Client -> Server)

All inherit from `EDMesgAction`.

| Class | Fields | Description |
|---|---|---|
| `GetEDAPLocationAction` | (none) | Request EDAP install path |
| `LoadWaypointFileAction` | `filepath: str` | Load a waypoint file by path |
| `StartWaypointAssistAction` | (none) | Start waypoint assist mode |
| `StopAllAssistsAction` | (none) | Stop all running assists |
| `LaunchAction` | (none) | Request ship launch/undock |
| `SystemMapTargetStationByBookmarkAction` | `type: str`, `number: int` | Set system map destination by bookmark |
| `GalaxyMapTargetStationByBookmarkAction` | `type: str`, `number: int` | Set galaxy map destination by bookmark |
| `GalaxyMapTargetSystemByNameAction` | `name: str` | Set galaxy map destination by system name |
| `GenericAction` | `name: str` | Generic named action |

## Event Classes (Server -> Client)

All inherit from `EDMesgEvent`.

| Class | Fields | Description |
|---|---|---|
| `EDAPLocationEvent` | `path: str` | EDAP install directory path |
| `LaunchCompleteEvent` | (none) | Ship launch completed |

## Module-Level Data

| Symbol | Type | Description |
|---|---|---|
| `provider_name` | str | `"EDAP"` -- provider identity |
| `actions` | list[type] | All 9 action types registered with EDMesg |
| `events` | list[type] | All 2 event types registered with EDMesg |

## Factory Functions

| Function | Returns | Description |
|---|---|---|
| `create_edap_provider(actions_port, events_port)` | EDMesgProvider | Creates an EDMesg provider with EDAP action/event types. Used by `EDMesgServer`. |
| `create_edap_client(actions_port, events_port)` | EDMesgClient | Creates an EDMesg client that can send actions and receive events. Used by external tools. |

## Dependencies

| Module | Purpose |
|---|---|
| `EDMesg.EDMesgBase` | `EDMesgAction`, `EDMesgEvent` base classes |
| `EDMesg.EDMesgProvider` | Provider class for server-side |
| `EDMesg.EDMesgClient` | Client class for client-side |

## Notes

- Action and event classes use pydantic-style field declarations (from EDMesg base)
- Port numbers are passed as parameters (no hardcoded defaults)
- Provider name `"EDAP"` identifies this provider in the EDMesg ecosystem
- Both provider and client factories share the same action/event type lists
