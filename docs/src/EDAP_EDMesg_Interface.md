# EDAP_EDMesg_Interface.py

## Purpose
Defines EDAP-specific action and event types for EDMesg messaging, plus factory methods to create provider and client instances.

## Key Classes/Functions
- GetEDAPLocationAction: Request EDAP installation directory
- LoadWaypointFileAction: Load waypoint file with filepath parameter
- StartWaypointAssistAction: Begin waypoint navigation
- StopAllAssistsAction: Cancel all active assists
- LaunchAction: Trigger launch sequence
- SystemMapTargetStationByBookmarkAction: Set system map destination by bookmark
- GalaxyMapTargetStationByBookmarkAction: Set galaxy map destination by bookmark
- GalaxyMapTargetSystemByNameAction: Set galaxy map destination by system name
- GenericAction: Generic action with name parameter
- EDAPLocationEvent: Responds with EDAP installation path
- LaunchCompleteEvent: Signals launch operation completed
- create_edap_provider(actions_port, events_port): Factory for EDMesgProvider
- create_edap_client(actions_port, events_port): Factory for EDMesgClient

## Key Methods
None (classes are data containers)

## Dependencies
- EDMesg.EDMesgBase: EDMesgAction, EDMesgEvent base classes
- EDMesg.EDMesgProvider: Provider implementation
- EDMesg.EDMesgClient: Client implementation

## Notes
- All actions and events derive from Pydantic BaseModel for serialization
- Provider name is "EDAP"
- Factory methods simplify instantiation with consistent configuration
- Socket ports must be provided at runtime
