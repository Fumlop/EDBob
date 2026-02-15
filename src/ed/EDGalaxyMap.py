from __future__ import annotations

import re

import cv2
import numpy as np
import easyocr

from src.core.EDAP_data import GuiFocusGalaxyMap
from src.screen.Screen_Regions import scale_region, Quad, load_calibrated_regions
from src.ed.StatusParser import StatusParser
from time import sleep
from src.core.EDlogger import logger

# Lazy-loaded EasyOCR reader (heavy init, only create once)
_easyocr_reader = None


def _get_ocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _easyocr_reader


# Favorites list text region as fraction of screen (for 1440x900 game window)
# Excludes icon sidebar, captures only the text column of the favorites list
FAV_LIST_REGION_PCT = [0.076, 0.172, 0.215, 0.522]  # [L, T, R, B] in percent


class EDGalaxyMap:
    """ Handles the Galaxy Map. """
    def __init__(self, ed_ap, screen, keys, cb, is_odyssey=True):
        self.ap = ed_ap
        self.ocr = ed_ap.ocr
        self.is_odyssey = is_odyssey
        self.screen = screen
        self.keys = keys
        self.status_parser = StatusParser()
        self.ap_ckb = cb
        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        self.reg = {'full_panel': {'rect': [0.1, 0.1, 0.9, 0.9]},
                    'cartographics': {'rect': [0.0, 0.0, 0.15, 0.15]},
                    'fav_list': {'rect': FAV_LIST_REGION_PCT},
                    }
        self.SystemSelectDelay = 0.5  # Delay selecting the system when in galaxy map

        # Load custom regions from file
        load_calibrated_regions('EDGalaxyMap', self.reg)

    # ---- Favorites OCR ----

    def _ocr_favorites_list(self) -> list[tuple[int, str, int]]:
        """OCR the visible favorites list and return detected numbered entries.
        @return: List of (number, name, y_position) sorted by y_position (top to bottom).
        """
        # Grab the favorites list region from screen
        image = self.screen.get_screen_rect_pct(self.reg['fav_list']['rect'])
        if image is None:
            logger.warning("Failed to grab favorites list region")
            return []

        # Isolate white text (favorite names are white, subtitles are orange)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 160])
        upper_white = np.array([180, 60, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Run OCR
        reader = _get_ocr_reader()
        results = reader.readtext(mask, detail=1)

        # Parse results for -N- pattern (OCR drops leading dash)
        pattern = re.compile(r'(\d+)-(.+)')
        entries = []
        for (bbox, text, score) in results:
            text_clean = text.strip()
            m = pattern.match(text_clean)
            if m:
                num = int(m.group(1))
                name = m.group(2).strip()
                y_pos = int(bbox[0][1])
                if num >= 1:  # 0- prefix = not a waypoint (e.g. carrier)
                    entries.append((num, name, y_pos))
                    logger.debug(f"Favorites OCR: #{num} '{name}' y={y_pos} score={score:.3f}")

        # Sort by Y position (top to bottom = list order)
        entries.sort(key=lambda x: x[2])
        return entries

    def _open_favorites_panel(self) -> bool:
        """Open galaxy map and navigate to the FAVOURITES bookmark list.
        @return: True if successfully opened.
        """
        res = self.goto_galaxy_map()
        if not res:
            return False

        # From search bar: go left to BOOKMARKS
        self.keys.send('UI_Left')
        sleep(0.5)
        self.keys.send('UI_Select')  # Open BOOKMARKS
        sleep(0.25)
        self.keys.send('UI_Right')   # Move to list type (FAVOURITES is first)
        sleep(0.25)
        self.keys.send('UI_Select')  # Select FAVOURITES, cursor moves to list
        sleep(0.5)
        return True

    def select_favorite_by_number(self, target_number: int) -> bool:
        """Open galaxy map favorites and select the entry with the given number prefix.
        Naming convention: in-game favorite named '-N-NAME', OCR reads as 'N-NAME'.
        @param target_number: The waypoint number to select (1, 2, 3...).
        @return: True if waypoint found and route plotted.
        """
        if not self._open_favorites_panel():
            return False

        # Wait for list to render
        sleep(0.5)

        # OCR the favorites list
        entries = self._ocr_favorites_list()
        if not entries:
            logger.warning("No numbered favorites found in list")
            self.keys.send('GalaxyMapOpen')  # Close galmap
            sleep(0.5)
            return False

        # Find the target entry and its position in the visible list
        target_idx = None
        for i, (num, name, y_pos) in enumerate(entries):
            if num == target_number:
                target_idx = i
                logger.info(f"Found favorite #{num}: '{name}' at list position {i}")
                break

        if target_idx is None:
            logger.info(f"Favorite #{target_number} not found in visible list")
            self.keys.send('GalaxyMapOpen')  # Close galmap
            sleep(0.5)
            return False

        # The cursor is already on the first item in the list.
        # All numbered entries (>=1) sort after 0-entries in the alphabetical list.
        # We need to figure out how many presses from the top of the list to reach
        # our target. The entries list only contains numbered waypoints (>=1),
        # but there may be non-waypoint items above them (like 0-HOMECARRIER).
        #
        # Strategy: use the Y positions from OCR to determine the list index.
        # The first OCR entry with the smallest Y is closest to list position 0,
        # but we don't know how many non-numbered items are above it.
        #
        # Simpler approach: the favorites are sorted alphabetically.
        # '-1-...' sorts before '-2-...' which sorts before 'BANKS...' etc.
        # So numbered entries (-1-, -2-) are at the TOP of the list,
        # right after any 0- entries.
        #
        # We navigate: first item = list position 0. Our target is at the
        # position of the target within ALL entries starting with dash-number.
        # Since 0- items are before 1-, we need to account for those.

        # OCR all entries including 0-prefixed ones to count offset
        image = self.screen.get_screen_rect_pct(self.reg['fav_list']['rect'])
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 0, 160]), np.array([180, 60, 255]))
        reader = _get_ocr_reader()
        all_results = reader.readtext(mask, detail=1)

        # Count entries above our target by Y position
        target_y = entries[target_idx][2]
        items_above = 0
        for (bbox, text, score) in all_results:
            text_clean = text.strip().upper()
            y = int(bbox[0][1])
            # Skip header text like "FAVOURITES"
            if text_clean in ('FAVOURITES', 'BOOKMARKS', 'FAVORITES'):
                continue
            if y < target_y and score > 0.3:
                items_above += 1

        logger.debug(f"Navigating {items_above} items down to reach #{target_number}")

        # Navigate down to target
        if items_above > 0:
            self.keys.send('UI_Down', repeat=items_above)
            sleep(0.25)

        # Long-press select to plot route
        self.keys.send('UI_Select', hold=3.0)
        sleep(0.5)

        # Close Galaxy map
        self.keys.send('GalaxyMapOpen')
        sleep(0.5)
        return True

    def get_available_favorites(self) -> list[int]:
        """Return list of waypoint numbers found in the favorites list.
        Must be called while favorites panel is already open.
        """
        entries = self._ocr_favorites_list()
        return [num for num, name, y in entries]

    # ---- Legacy methods (kept for compatibility) ----

    def set_gal_map_dest_bookmark(self, ap, bookmark_type: str, bookmark_position: int) -> bool:
        """ Set the gal map destination using a bookmark.
        @param ap: ED_AP reference.
        @param bookmark_type: The bookmark type (Favorite, System, Body, Station or Settlement), Favorite
         being the default if no match is made with the other options.
        @param bookmark_position: The position in the bookmark list, starting at 1 for the first bookmark.
        @return: True if bookmark could be selected, else False
        """
        if self.is_odyssey and bookmark_position > 0:
            res = self.goto_galaxy_map()
            if not res:
                return False

            ap.keys.send('UI_Left')  # Go to BOOKMARKS
            sleep(.5)
            ap.keys.send('UI_Select')  # Select BOOKMARKS
            sleep(.25)
            ap.keys.send('UI_Right')  # Go to FAVORITES
            sleep(.25)

            # If bookmark type is Fav, do nothing as this is the first item
            if bookmark_type.lower().startswith("sys"):
                ap.keys.send('UI_Down')  # Go to SYSTEMS
            elif bookmark_type.lower().startswith("bod"):
                ap.keys.send('UI_Down', repeat=2)  # Go to BODIES
            elif bookmark_type.lower().startswith("sta"):
                ap.keys.send('UI_Down', repeat=3)  # Go to STATIONS
            elif bookmark_type.lower().startswith("set"):
                ap.keys.send('UI_Down', repeat=4)  # Go to SETTLEMENTS

            sleep(.25)
            ap.keys.send('UI_Select')  # Select bookmark type, moves you to bookmark list
            sleep(.25)
            ap.keys.send('UI_Down', repeat=bookmark_position - 1)
            sleep(.25)
            ap.keys.send('UI_Select', hold=3.0)

            # Close Galaxy map
            ap.keys.send('GalaxyMapOpen')
            sleep(0.5)
            return True

        return False

    def set_gal_map_destination_text(self, ap, target_name, target_select_cb=None) -> bool:
        """ Call either the Odyssey or Horizons version of the Galactic Map sequence. """
        if not self.is_odyssey:
            return ap.galaxy_map.set_gal_map_destination_text_horizons(ap, target_name, target_select_cb)
        else:
            return ap.galaxy_map.set_gal_map_destination_text_odyssey(ap, target_name)

    def set_gal_map_destination_text_horizons(self, ap, target_name, target_select_cb=None) -> bool:
        """ This sequence for the Horizons. """
        res = self.goto_galaxy_map()
        if not res:
            return False

        ap.keys.send('CycleNextPanel')
        sleep(1)
        ap.keys.send('UI_Select')
        sleep(2)

        from pyautogui import typewrite
        typewrite(target_name, interval=0.25)
        sleep(1)

        # send enter key
        ap.keys.send_key('Down', 28)
        sleep(0.05)
        ap.keys.send_key('Up', 28)

        sleep(7)
        ap.keys.send('UI_Right')
        sleep(1)
        ap.keys.send('UI_Select')

        if target_select_cb is not None:
            while not target_select_cb()['target']:
                sleep(1)

        # Close Galaxy map
        ap.keys.send('GalaxyMapOpen')
        sleep(2)
        return True

    def set_gal_map_destination_text_odyssey(self, ap, target_name) -> bool:
        """ This sequence for the Odyssey. """
        res = self.goto_galaxy_map()
        if not res:
            return False

        target_name_uc = target_name.upper()

        # Check if the current nav route is to the target system
        last_nav_route_sys = ap.nav_route.get_last_system()
        last_nav_route_sys_uc = last_nav_route_sys.upper()
        if last_nav_route_sys_uc == target_name_uc:
            # Close Galaxy map
            ap.keys.send('GalaxyMapOpen')
            return True

        # navigate to and select: search field
        ap.keys.send('UI_Up')
        sleep(0.05)
        ap.keys.send('UI_Select')
        sleep(0.05)

        from pyautogui import typewrite
        # type in the System name
        typewrite(target_name_uc, interval=0.25)
        logger.debug(f"Entered system name: {target_name_uc}.")
        sleep(0.05)

        # send enter key (removes focus out of input field)
        ap.keys.send_key('Down', 28)  # 28=ENTER
        sleep(0.05)
        ap.keys.send_key('Up', 28)  # 28=ENTER
        sleep(0.05)

        ap.keys.send('UI_Down')
        sleep(0.05)
        ap.keys.send('UI_Up')
        sleep(0.05)

        # navigate to and select: search button
        ap.keys.send('UI_Right')  # to >| button
        sleep(0.05)

        correct_route = False
        while not correct_route:
            last_nav_route_sys = ap.nav_route.get_last_system()
            last_nav_route_sys_uc = last_nav_route_sys.upper()
            logger.debug(f"Previous Nav Route dest: {last_nav_route_sys_uc}.")

            ap.keys.send('UI_Select')  # Select >| button
            sleep(self.SystemSelectDelay)

            ap.keys.send('CamZoomIn')
            sleep(0.5)

            ap.keys.send('UI_Select', hold=0.75)
            sleep(0.05)

            if ap.nav_route is not None:
                logger.debug(f"Waiting for Nav Route to update.")
                while 1:
                    curr_nav_route_sys = ap.nav_route.get_last_system()
                    curr_nav_route_sys_uc = curr_nav_route_sys.upper()
                    if curr_nav_route_sys_uc != last_nav_route_sys_uc:
                        logger.debug(f"Nav Route dest changed from: {last_nav_route_sys_uc} to: {curr_nav_route_sys_uc}.")
                        if curr_nav_route_sys_uc == target_name_uc:
                            logger.debug(f"Nav Route correctly updated to {target_name_uc}.")
                            correct_route = True
                            break
                        else:
                            logger.debug(f"Nav Route updated with wrong target: {curr_nav_route_sys_uc}. Select next target.")
                            ap.keys.send('UI_Up')
                            break
            else:
                logger.debug(f"Unable to check Nav Route, so assuming it is correct.")
                correct_route = True

        # Close Galaxy map
        ap.keys.send('GalaxyMapOpen')
        sleep(0.5)
        return True

    def set_next_system(self, ap, target_system) -> bool:
        """ Sets the next system to jump to, or the final system to jump to. """
        if self.set_gal_map_destination_text(ap, target_system, None):
            return True
        else:
            logger.warning("Error setting waypoint, breaking")
            return False

    def goto_galaxy_map(self) -> bool:
        """Open Galaxy Map if we are not there. Waits for map to load. Selects the search bar."""
        if self.status_parser.get_gui_focus() != GuiFocusGalaxyMap:
            logger.debug("Opening Galaxy Map")
            # Goto cockpit view
            self.ap.ship_control.goto_cockpit_view()
            # Goto Galaxy Map
            self.keys.send('GalaxyMapOpen')

            if self.ap.debug_overlay:
                stn_svcs = Quad.from_rect(self.reg['full_panel']['rect'])
                self.ap.overlay.overlay_quad_pct('system map', stn_svcs, (0, 255, 0), 2, 5)
                self.ap.overlay.overlay_paint()

            # Wait for screen to appear. The text is the same, regardless of language.
            res = self.ocr.wait_for_ui_element(self.ap, self.reg['cartographics'], timeout=15)
            if not res:
                if self.status_parser.get_gui_focus() != GuiFocusGalaxyMap:
                    logger.warning("Unable to open Galaxy Map")
                    return False

            self.keys.send('UI_Up')  # Go up to search bar
            return True
        else:
            logger.debug("Galaxy Map is already open")
            self.keys.send('UI_Left', repeat=2)
            self.keys.send('UI_Up', hold=2)  # Go up to search bar
            return True
