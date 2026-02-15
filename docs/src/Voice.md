# Voice.py

## Purpose
Text-to-speech voice notification system using pyttsx3. Runs voice synthesis in a background daemon thread with queue-based command handling.

## Key Classes/Functions
- Voice: Text-to-speech wrapper managing voice synthesis in background thread

## Key Methods
- say(vSay): Queues text for speech synthesis if voice is enabled
- set_on(): Enables voice synthesis
- set_off(): Disables voice synthesis (messages still queued but not spoken)
- set_voice_id(id): Sets voice ID (0=David, 1=Zira, etc. system-dependent)
- quit(): Signals background thread to exit
- voice_exec(): Background thread function that processes queue and runs speech engine

## Features
- Non-blocking queue-based speech (up to 5 messages)
- Background daemon thread (KThread for killability)
- Voice ID switching without restarting engine
- Speech rate 160 WPM (configurable)
- Pronunciation corrections: ' Mk V ' -> ' mark five ', ' Mk ' -> ' mark ', ' Krait ' -> ' crate '

## Dependencies
- pyttsx3: Cross-platform text-to-speech engine
- kthread: Killable thread implementation for clean shutdown
- queue: Thread-safe message queue
- threading: Threading primitives

## Notes
- Daemon thread exits gracefully when quit() called
- Thread-safe queue prevents blocking main thread
- Handles voice list from system (voices[0]=male, voices[1]=female typical)
- Catches exceptions for out-of-range voice IDs
- Game-specific pronunciation corrections included
