# EDMesg/EDMesgBase.py

## Purpose
Provides abstract base classes and envelope structure for EDMesg messaging protocol.

## Key Classes/Functions
- EDMesgAction: Abstract base class for all action messages
- EDMesgWelcomeAction: Special action sent when client connects
- EDMesgEvent: Abstract base class for all event messages
- EDMesgEnvelope: Wrapper that serializes type name and data for transmission

## Key Methods
None (classes are data containers using Pydantic BaseModel)

## Dependencies
- abc: Abstract base class support
- pydantic: BaseModel for serialization/validation

## Notes
- All classes derive from Pydantic BaseModel for automatic JSON serialization
- EDMesgEnvelope packages message type as string and data as dict for wire format
- EDMesgWelcomeAction serves as implicit connection indicator
- ABC inheritance not strictly enforced by Pydantic but provides intent
