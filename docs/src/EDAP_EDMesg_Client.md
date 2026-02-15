# EDAP_EDMesg_Client.py

## Purpose
Implements a client wrapper for connecting to EDAP through EDMesg, handling action dispatch and event reception on separate threads.

## Key Classes/Functions
- EDMesgClient: High-level client that manages connection to EDAP and communication loop
- main(): Entry point that creates and maintains the client instance

## Key Methods
- __init__(ed_ap, cb): Initializes client with EDAP reference and callback, creates underlying EDMesg client and starts background loop
- _client_loop(): Daemon thread that polls for incoming events and dispatches handlers
- _handle_launch_complete(): Processes LaunchCompleteEvent from EDAP
- send_launch_action(): Publishes LaunchAction to EDAP

## Dependencies
- threading: For background communication loop
- EDAP_EDMesg_Interface: Factory methods and action/event types (LaunchAction, LaunchCompleteEvent)
- EDMesg.EDMesgClient: Low-level messaging client

## Notes
- Client runs background thread to avoid blocking main application thread
- Currently minimal event handling (only LaunchCompleteEvent)
- Actions and events ports hardcoded (15570, 15571)
- Exception handling is basic (bare except)
