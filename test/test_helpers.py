"""Shared helpers for standalone tests."""
import atexit
import os
from time import sleep


COUNTDOWN_SECS = 7


def countdown(seconds=COUNTDOWN_SECS, msg="Starting test"):
    """Countdown timer so user can alt-tab to Elite."""
    print(f"\n  >>> {msg} in {seconds}s -- switch to Elite! <<<")
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end=" ", flush=True)
        sleep(1.0)
    print("GO!\n")


def dummy_cb(msg, body=None):
    if body:
        print(f"[CB] {msg}: {body}")
    else:
        print(f"[CB] {msg}")


def create_autopilot():
    """Create EDAutopilot with countdown so user can focus Elite first.
    Also initializes ship type and config from journal so pitch/roll/yaw work standalone.
    """
    countdown(msg="Initializing autopilot -- focus Elite!")
    from src.autopilot.ED_AP import EDAutopilot
    from src.screen.Screen import Screen
    from src.screen import Screen_Regions

    ap = EDAutopilot(cb=dummy_cb, doThread=False)
    ap.keys.activate_window = True

    # Debug screen detection
    print(f"  Screen (first init): {ap.scr.screen_width}x{ap.scr.screen_height} "
          f"at ({ap.scr.screen_left},{ap.scr.screen_top}) mon={ap.scr.monitor_number}")
    ed_rect = ap.scr.get_elite_window_rect()
    ed_client = ap.scr.get_elite_client_rect()
    print(f"  ED window rect:  {ed_rect}")
    print(f"  ED client rect:  {ed_client}")

    # If screen dims look wrong, reinit
    if ap.scr.screen_width <= 0 or ap.scr.screen_height <= 0 or ap.scr.screen_width > 7680:
        print("  Screen dims look wrong, reinitializing...")
        ap.scr = Screen(cb=dummy_cb)
        ap.scrReg = Screen_Regions.Screen_Regions(ap.scr)
        print(f"  Screen (reinit):  {ap.scr.screen_width}x{ap.scr.screen_height} "
              f"at ({ap.scr.screen_left},{ap.scr.screen_top}) mon={ap.scr.monitor_number}")

    # Init ship type from journal (normally done in main AP loop)
    ship = ap.jn.ship_state().get('type')
    if ship:
        ap.current_ship_type = ship
        ap.load_ship_configuration(ship)
        print(f"  Ship: {ship}")
    else:
        print("  WARNING: Could not detect ship type from journal")

    # Force exit when tests complete -- overlay thread blocks normal shutdown
    atexit.register(lambda: os._exit(0))

    return ap
