# EDMesg/EDMesgClient.py

## Purpose
Low-level ZMQ-based client for EDMesg message broker pattern, handles action publishing and event subscription.

## Key Classes/Functions
- EDMesgClient: Final class implementing push-subscribe pattern for message exchange

## Key Methods
- __init__(provider_name, action_types, event_types, action_port, event_port): Sets up ZMQ sockets and listener thread
- publish(action): Serializes and sends EDMesgAction to provider via PUSH socket
- _listen_events(): Daemon thread receiving events from PUB socket and queuing them
- _instantiate_event(type_name, data): Reconstructs event object from envelope data
- close(): Stops listener thread and closes all sockets

## Dependencies
- zmq: ZMQ messaging (PUSH/SUB pattern)
- threading: Event listener thread
- queue: Queue for pending events
- pydantic: For message serialization
- tempfile/os: Socket path generation (unused, commented out)

## Notes
- Uses TCP sockets (127.0.0.1) not IPC despite ipc path generation code
- PUSH socket for actions, SUB socket for events (opposite of provider)
- Non-blocking socket operations with sleep to prevent busy-waiting
- Thread-safe pending_events queue
- EDMesgWelcomeAction auto-added to accepted action types
- Designed to be instantiated only once per instance (marked @final)
