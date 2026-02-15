# EDMesg/EDMesgProvider.py

## Purpose
Low-level ZMQ-based provider (server) for EDMesg message broker pattern, handles action reception and event publishing.

## Key Classes/Functions
- EDMesgProvider: Final class implementing pull-publish pattern for message exchange

## Key Methods
- __init__(provider_name, action_types, event_types, action_port, event_port): Sets up ZMQ sockets and listener threads
- publish(event): Serializes and broadcasts EDMesgEvent to all subscribed clients
- _listen_actions(): Daemon thread receiving actions from PULL socket and queuing them
- _listen_status(): Daemon thread monitoring client connections via socket monitor
- _instantiate_action(type_name, data): Reconstructs action object from envelope data
- close(): Stops listener threads, closes sockets, cleans up socket files

## Dependencies
- zmq: ZMQ messaging (PULL/PUB pattern)
- threading: Action and status listener threads
- queue: Queue for pending actions
- pydantic: For message serialization
- tempfile/os: Socket path generation and cleanup

## Notes
- Uses TCP sockets (127.0.0.1) not IPC despite ipc path generation code
- PULL socket for actions, PUB socket for events (opposite of client)
- Non-blocking socket operations with sleep to prevent busy-waiting
- Monitors client handshake events and injects EDMesgWelcomeAction on new connection
- Socket files cleaned up in __init__ and close()
- EDMesgWelcomeAction auto-added to accepted action types
- Two daemon threads for independent message streams
- Designed to be instantiated only once per instance (marked @final)
