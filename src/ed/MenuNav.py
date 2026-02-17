from __future__ import annotations

from time import sleep

from src.core import EDAP_data
from src.core.EDAP_data import (
    GuiFocusNoFocus, GuiFocusExternalPanel, GuiFocusStationServices
)
from src.core.EDlogger import logger
from src.ed.StatusParser import StatusParser

"""
File: MenuNav.py

Description:
  Consolidated menu/UI navigation functions for Elite Dangerous.
  Replaces scattered menu key sequences across ED_AP, EDNavigationPanel,
  EDStationServicesInShip, and EDShipControl with clean, reusable functions.

  All functions take keys (EDKeys) and status_parser (StatusParser) as params
  so they stay stateless -- no class needed.
"""


def goto_cockpit(keys, status_parser: StatusParser, max_tries: int = 10) -> bool:
    """Close all menus by sending UI_Back until gui_focus == NoFocus.
    Returns True once in cockpit view, False if max_tries exceeded.
    """
    if status_parser.get_gui_focus() == GuiFocusNoFocus:
        return True

    for _ in range(max_tries):
        keys.send("UI_Back")
        sleep(0.3)
        if status_parser.get_gui_focus() == GuiFocusNoFocus:
            return True

    logger.warning(f"goto_cockpit: still in focus {status_parser.get_gui_focus()} after {max_tries} tries")
    return False


def realign_cursor(keys, hold: float = 3):
    """Move cursor to the top of any menu list.
    Uses UI_Up with a hold duration to ensure we're at position 0.
    """
    keys.send('UI_Up', hold=hold)


def refuel_repair_rearm(keys, status_parser: StatusParser):
    """From the docked station menu (post-autodock), refuel, repair, rearm
    then close the menu back to cockpit view.

    Menu layout (cursor at top after realign):
      Row 0: Refuel
      Row 0 + Right: Repair
      Row 0 + Right + Right: Rearm
    """
    realign_cursor(keys, hold=3)
    keys.send('UI_Select')   # Refuel
    sleep(0.5)
    keys.send('UI_Right')    # move to Repair
    keys.send('UI_Select')   # Repair
    sleep(0.5)
    keys.send('UI_Right')    # move to Rearm
    keys.send('UI_Select')   # Rearm
    sleep(0.5)
    goto_cockpit(keys, status_parser)


def open_station_services(keys, status_parser: StatusParser) -> bool:
    """From the docked menu, navigate to Station Services.

    Menu layout (cursor at top after realign):
      Row 0: Refuel
      Row 1: Station Services
    Returns True if Station Services opened successfully.
    """
    goto_cockpit(keys, status_parser)

    realign_cursor(keys, hold=3)
    sleep(0.3)
    keys.send('UI_Select')   # select refuel line (enters that row)
    sleep(0.3)
    keys.send('UI_Down')     # down to Station Services
    sleep(0.3)
    keys.send('UI_Select')   # open Station Services

    return status_parser.wait_for_gui_focus(GuiFocusStationServices, timeout=15)


def undock(keys, status_parser: StatusParser):
    """From the docked station menu, navigate to Auto Undock and select it.

    Menu layout (cursor at top after realign):
      Row 0: Refuel
      Row 1: Station Services
      Row 2: Auto Undock (Launch)
    """
    goto_cockpit(keys, status_parser)

    realign_cursor(keys, hold=3)
    keys.send('UI_Down')     # Station Services
    keys.send('UI_Down')     # Auto Undock
    keys.send('UI_Select')   # Launch


def open_nav_panel(keys, status_parser: StatusParser) -> bool:
    """Open the left-hand Navigation panel.
    Returns True if panel opened, False on timeout.
    """
    keys.send('FocusLeftPanel')
    sleep(0.5)
    return status_parser.wait_for_gui_focus(GuiFocusExternalPanel, timeout=3)


def close_nav_panel(keys):
    """Close the Navigation panel with UI_Back."""
    keys.send('UI_Back')
    sleep(0.3)


def activate_sc_assist(keys, status_parser: StatusParser, is_target_row_fn, cb=None) -> bool:
    """Open nav panel, find the target row, and activate Supercruise Assist.

    @param is_target_row_fn: callable(seen_bracket: list) -> bool
        Checks if the currently highlighted row is the locked target.
    @param cb: optional callback for log messages, signature cb(str, str)
    Returns True if SC Assist was activated.
    """
    if not open_nav_panel(keys, status_parser):
        logger.warning("activate_sc_assist: nav panel did not open")
        return False

    # Go to top of list
    realign_cursor(keys, hold=2)
    sleep(1.0)

    # Step down row by row, check for target bracket
    max_rows = 20
    found = False
    seen_bracket = [False]
    for step in range(max_rows):
        sleep(0.5)
        if is_target_row_fn(seen_bracket):
            logger.info(f"activate_sc_assist: found target at step {step}")
            if cb:
                cb('log', f'SC Assist: target found at row {step}')
            found = True
            break
        keys.send('UI_Down')

    if not found:
        logger.warning("activate_sc_assist: target row not found after stepping through list")
        if cb:
            cb('log', 'SC Assist: target not found in nav panel')
        keys.send('UI_Back', repeat=2)
        sleep(0.3)
        return False

    # Open target detail page
    keys.send('UI_Select')
    sleep(1.0)

    # Navigate to SC Assist button and select
    keys.send('UI_Right')
    sleep(0.3)
    keys.send('UI_Select')
    sleep(0.5)

    logger.info("activate_sc_assist: SC Assist activation sequence completed")
    if cb:
        cb('log', 'SC Assist activated')

    # Close nav panel
    keys.send('UI_Back', repeat=2)
    sleep(0.5)
    return True


def request_docking(keys, status_parser: StatusParser) -> bool:
    """Request docking via nav panel: open panel, cycle to Contacts tab,
    select action on first entry, cycle back, close.
    Returns True if sequence completed.
    """
    if not open_nav_panel(keys, status_parser):
        logger.warning("request_docking: nav panel did not open")
        return False

    # Navigation -> Contacts (2 tabs right)
    logger.info("request_docking: cycling to Contacts tab")
    keys.send('CycleNextPanel')
    sleep(0.5)
    keys.send('CycleNextPanel')
    sleep(0.5)

    # First entry is already selected (the target), UI_Right to action button
    logger.info("request_docking: selecting target action")
    keys.send('UI_Right')
    sleep(0.5)
    keys.send('UI_Select')
    sleep(0.5)

    # Back to Navigation tab so panel state is clean for later
    logger.info("request_docking: cycling back to Navigation tab")
    keys.send('CyclePreviousPanel')
    sleep(0.5)
    keys.send('CyclePreviousPanel')
    sleep(0.5)

    close_nav_panel(keys)
    return True


def transfer_all_to_colonisation(keys):
    """Transfer all cargo to a colonisation/construction ship.
    Assumes the construction services screen is already open.

    Layout: table on left, buttons at bottom (RESET | CONFIRM TRANSFER | TRANSFER ALL).
    """
    keys.send('UI_Left', repeat=3)   # into table
    keys.send('UI_Down', hold=2)     # bottom of table
    keys.send('UI_Up')               # up to button row (RESET/CONFIRM/TRANSFER ALL)
    keys.send('UI_Left', repeat=2)   # leftmost = RESET
    keys.send('UI_Right', repeat=2)  # rightmost = TRANSFER ALL
    keys.send('UI_Select')           # select TRANSFER ALL
    sleep(0.5)

    keys.send('UI_Left')             # CONFIRM TRANSFER
    keys.send('UI_Select')           # confirm
    sleep(2)

    keys.send('UI_Down')             # EXIT
    keys.send('UI_Select')           # select EXIT
    sleep(2)
