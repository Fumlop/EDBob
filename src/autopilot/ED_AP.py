import json
import math
import os
import threading
import time
from copy import copy
from datetime import datetime, timedelta
from time import sleep
from math import asin, atan, degrees
from tkinter import messagebox

import cv2
import numpy as np
import kthread
from simple_localization import LocalizationManager



from src.core.EDAP_data import (
    FlagsDocked, FlagsLanded, FlagsLandingGearDown, FlagsSupercruise, FlagsFsdMassLocked,
    FlagsFsdCharging, FlagsFsdCooldown, FlagsFsdJump,
    FlagsHasLatLong, FlagsBeingInterdicted,
    FlagsAnalysisMode, Flags2FsdHyperdriveCharging,
    Flags2GlideMode, GuiFocusNoFocus, ship_size_map,
)
from src.core.directinput import SCANCODE
from src.core.EDlogger import logger, logging
from src.ed.EDGalaxyMap import EDGalaxyMap
from src.ed.EDGraphicsSettings import EDGraphicsSettings
from src.ed.EDShipControl import EDShipControl
from src.ed import MenuNav
from src.ed.EDStationServicesInShip import EDStationServicesInShip
from src.ed.EDSystemMap import EDSystemMap
from src.screen import Screen
from src.screen import Screen_Regions
from src.screen.Screen import set_focus_elite_window
from src.screen.Screen_Regions import Quad
from src.autopilot import EDWayPoint
from src.ed import EDJournal
from src.ed import EDKeys
from src.ed.EDInternalStatusPanel import EDInternalStatusPanel
from src.ed.NavRouteParser import NavRouteParser
from src.ed.EDNavigationPanel import EDNavigationPanel
from src.ed.StatusParser import StatusParser
from src.ship.Ship import Ship



"""
File:EDAP.py    EDBob

Description:

Note:
https://github.com/Fumlop/EDBob
"""


def read_json_file(filepath: str) -> dict | None:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def write_json_file(data: dict, filepath: str):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


def delete_old_log_files():
    """Delete .log files older than 5 days from the main folder."""
    current_time = time.time()
    day = 86400
    for filename in os.listdir('.'):
        if filename.endswith('.log') and os.path.isfile(filename):
            if os.path.getmtime(filename) < current_time - day * 5:
                logger.debug(f"Deleting old log: '{filename}'")
                os.remove(filename)


# Exception class used to unroll the call tree to to stop execution
class EDAP_Interrupt(Exception):
    pass



def scale(inp: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """ Does scaling of the input based on input and output min/max."""
    return (inp - in_min)/(in_max - in_min) * (out_max - out_min) + out_min


class EDAutopilot:

    # ------------------------------------------------------------------
    # Proxy properties -- delegate to self.ship for backwards compat.
    # Callers keep using self.pitchrate, self.ship_configs, etc.
    # ------------------------------------------------------------------
    def _ship_proxy(attr):
        """Create a property that proxies to self.ship.<attr>."""
        return property(
            lambda self: getattr(self.ship, attr),
            lambda self, v: setattr(self.ship, attr, v),
        )

    pitchrate      = _ship_proxy('pitchrate')
    rollrate       = _ship_proxy('rollrate')
    yawrate        = _ship_proxy('yawrate')
    sunpitchuptime = _ship_proxy('sunpitchuptime')
    pitchfactor    = _ship_proxy('pitchfactor')
    rollfactor     = _ship_proxy('rollfactor')
    yawfactor      = _ship_proxy('yawfactor')
    ship_configs   = _ship_proxy('ship_configs')
    current_ship_type = _ship_proxy('ship_type')
    speed_demand   = _ship_proxy('speed_demand')

    del _ship_proxy  # clean up helper from class namespace

    ZERO_THROTTLE_RATE_FACTOR = Ship.ZERO_THROTTLE_RATE_FACTOR

    def __init__(self, cb, doThread=True):
        self.config = {}
        self._prev_star_system = None
        # Load AP.json config
        self.load_config()

        # Load selected language
        self.locale = LocalizationManager('locales', self.config['Language'])

        # set log level based on config input, defaulting to warning
        logger.setLevel(logging.WARNING)
        if self.config['LogINFO']:
            logger.setLevel(logging.INFO)
        if self.config['LogDEBUG']:
            logger.setLevel(logging.DEBUG)

        # initialize all to false
        self.sc_assist_enabled = False
        self.waypoint_assist_enabled = False
        self.dss_assist_enabled = False
        self.calibrate_normal_enabled = False
        self.calibrate_sc_enabled = False
        self._stop_event = threading.Event()  # safe interrupt signal for assist threads

        # Create instance of each of the needed Classes
        self.scr = Screen.Screen(cb)
        self.scr.scaleX = self.config['ScreenScale']
        self.scr.scaleY = self.config['ScreenScale']

        self.gfx_settings = EDGraphicsSettings()
        if self.scr.aspect_ratio >= 1.7777:
            self.ver_fov = round(float(self.gfx_settings.fov), 4)
            logger.debug(f'Vertical FOV: {self.ver_fov} deg (-{self.ver_fov / 2} to {self.ver_fov / 2} deg).')
            self.hor_fov = round(self.ver_fov * self.scr.aspect_ratio, 4)
            logger.debug(f'Horizontal FOV: {self.hor_fov} deg (-{self.hor_fov / 2} to {self.hor_fov / 2} deg).')
        else:
            self.ver_fov = round(float(self.gfx_settings.fov) * (1.7777 / self.scr.aspect_ratio), 4)
            logger.debug(f'Vertical FOV: {self.ver_fov} deg (-{self.ver_fov / 2} to {self.ver_fov / 2}).')
            self.hor_fov = round(self.ver_fov * self.scr.aspect_ratio, 4)
            logger.debug(f'Horizontal FOV: {self.hor_fov} deg (-{self.hor_fov / 2} to {self.hor_fov / 2}).')

        self.scrReg = Screen_Regions.Screen_Regions(self.scr)
        self.jn = EDJournal.EDJournal(cb)
        self.keys = EDKeys.EDKeys(cb)
        self.waypoint = EDWayPoint.EDWayPoint(self, self.jn.ship_state()['odyssey'])
        self.status = StatusParser()
        self.nav_route = NavRouteParser()
        self.ship_control = EDShipControl(self, self.scr, self.keys, cb)
        self.internal_panel = EDInternalStatusPanel(self, self.scr, self.keys, cb)
        self.galaxy_map = EDGalaxyMap(self, self.scr, self.keys, cb, self.jn.ship_state()['odyssey'])
        self.system_map = EDSystemMap(self, self.scr, self.keys, cb, self.jn.ship_state()['odyssey'])
        self.stn_svcs_in_ship = EDStationServicesInShip(self, self.scr, self.keys, cb)
        self.nav_panel = EDNavigationPanel(self, self.scr, self.keys, cb)

        self.ap_ckb = cb

        # Ship: identity, rates, throttle, steering, calibration, config
        self.ship = Ship(self.keys, self.status, cb)
        self.ship.check_stop = self.check_stop

        # Load ship config for currently detected ship (if journal available)
        if self.jn:
            ship = self.jn.ship_state()['type']
            if ship:
                self.ship.load_ship_configuration(ship)

        self.jump_cnt = 0
        self._eta = 0
        self._str_eta = ''
        self.total_dist_jumped = 0
        self.total_jumps = 0
        self.refuel_cnt = 0
        self.gui_loaded = False
        self._nav_cor_x = 0.0  # Nav Point correction to pitch
        self._nav_cor_y = 0.0  # Nav Point correction to yaw
        self.target_align_outer_lim = 1.0  # In deg. Anything outside of this range will cause alignment.
        self.target_align_inner_lim = 0.5  # In deg. Will stop alignment when in this range.
        self.ap_state = "Idle"
        self.debug_images = False
        self.debug_image_folder = './debug-output/images'
        if not os.path.exists(self.debug_image_folder):
            os.makedirs(self.debug_image_folder)

        # debug window

        #start the engine thread
        self.terminate = False  # terminate used by the thread to exit its loop
        if doThread:
            self.ap_thread = kthread.KThread(target=self.engine_loop, name="EDAutopilot")
            self.ap_thread.start()

        # Start thread to delete old log files.
        del_log_files_thread = threading.Thread(target=delete_old_log_files, daemon=True)
        del_log_files_thread.start()

        # Process config[] settings to update classes as necessary
        self.process_config_settings()

    def update_config(self):
        # Get values from classes
        if self.keys:
            self.config['ActivateEliteEachKey'] = self.keys.activate_window
            self.config['Key_ModDelay'] = self.keys.key_mod_delay
            self.config['Key_DefHoldTime'] = self.keys.key_def_hold_time
            self.config['Key_RepeatDelay'] = self.keys.key_repeat_delay

        if self.waypoint:
            self.config['WaypointFilepath'] = self.waypoint.filename

        # Delete old settings
        self.config.pop('target_align_inertia_pitch_factor', None)
        self.config.pop('target_align_inertia_yaw_factor', None)

        write_json_file(self.config, filepath='./configs/AP.json')

    def load_config(self):
        """ Load AP.Json Config File. """
        self.config = {
            "DSSButton": "Primary",  # if anything other than "Primary", it will use the Secondary Fire button for DSS
            "JumpTries": 3,  #
            "NavAlignTries": 3,  #
            "RefuelThreshold": 65,  # if fuel level get below this level, it will attempt refuel
            "FuelThresholdAbortAP": 10, # level at which AP will terminate, because we are not scooping well
            "WaitForAutoDockTimer": 240, # After docking granted, wait this amount of time for us to get docked with autodocking
            "SunBrightThreshold": 125, # The low level for brightness detection, range 0-255, want to mask out darker items
            "FuelScoopTimeOut": 35, # number of second to wait for full tank, might mean we are not scooping well or got a small scooper
            "DockingRetries": 30,  # number of time to attempt docking
            "HotKey_StartFSD": "home",  # if going to use other keys, need to look at the python keyboard package
            "HotKey_StartSC": "ins",  # to determine other keynames, make sure these keys are not used in ED bindings
            "HotKey_StopAllAssists": "ctrl+x",
            "ActivateEliteEachKey": False,  # Activate Elite window before each key or group of keys
            "LogDEBUG": False,  # enable for debug messages
            "LogINFO": True,
            "ShipConfigFile": None,  # Ship config to load on start - deprecated
            "TargetScale": 1.0,  # Scaling of the target when a system is selected
            "ScreenScale": 1.0,  # Scaling of the target when a system is selected
            "AutomaticLogout": False,  # Logout when we are done with the mission
            "OCDepartureAngle": 55.0,  # Angle to pitch up when departing non-starport stations
            "Language": 'en',  # Language (matching ./locales/xx.json file)
            "HotkeysEnable": False,  # Enable hotkeys
            "WaypointFilepath": "",  # The previous waypoint file path
            "DebugImages": False,  # For debug, write debug images to output folder
            "Key_ModDelay": 0.01,  # Delay for key modifiers to ensure modifier is detected before/after the key
            "Key_DefHoldTime": 0.2,  # Default hold time for a key press
            "Key_RepeatDelay": 0.1,  # Delay between key press repeats
            "target_align_outer_lim": 1.0,  # For test
            "target_align_inner_lim": 0.5,  # For test
            "GalMap_SystemSelectDelay": 0.5,  # Delay selecting the system when in galaxy map
            "PlanetDepartureSCOTime": 5.0,  # SCO boost time when leaving planet in secs
            "FleetCarrierMonitorCAPIDataPath": "",  # EDMC Fleet Carrier Monitor plugin data export path
        }
        cnf = read_json_file(filepath='./configs/AP.json')
        # if we read it then point to it, otherwise use the default table above
        if cnf is not None:
            # Fill missing keys from defaults
            for key, value in self.config.items():
                cnf.setdefault(key, value)
            # Migrate old typo key
            if 'FuelThreasholdAbortAP' in cnf:
                cnf.setdefault('FuelThresholdAbortAP', cnf.pop('FuelThreasholdAbortAP'))
            self.config = cnf
            logger.debug("read AP json:" + str(cnf))
        else:
            write_json_file(self.config, filepath='./configs/AP.json')

    def load_ship_configs(self):
        """Reload ship configs from disk and apply to current ship."""
        self.ship.load_ship_configs()
        if self.jn:
            ship = self.jn.ship_state()['type']
            if ship:
                self.ship.load_ship_configuration(ship)

    def update_ship_configs(self):
        """Save current ship rates to ship_configs.json."""
        self.ship.save_ship_configs()

    def load_ship_configuration(self, ship_type):
        """Load config for a specific ship type."""
        self.ship.load_ship_configuration(ship_type)

    def update_ap_status(self, txt):
        self.ap_state = txt
        self.ap_ckb('statusline', txt)

    def process_config_settings(self):
        """ Update subclasses as necessary with config setting changes. """
        if self.keys:
            self.keys.activate_window = self.config['ActivateEliteEachKey']
            self.keys.key_mod_delay = self.config['Key_ModDelay']
            self.keys.key_def_hold_time = self.config['Key_DefHoldTime']
            self.keys.key_repeat_delay = self.config['Key_RepeatDelay']

        if self.galaxy_map:
            self.galaxy_map.SystemSelectDelay = self.config['GalMap_SystemSelectDelay']

        self.target_align_outer_lim = self.config['target_align_outer_lim']
        self.target_align_inner_lim = self.config['target_align_inner_lim']

        self.debug_images = self.config['DebugImages']

    def have_destination(self, scr_reg) -> bool:
        """ Check to see if the compass is on the screen. """
        res = self.get_nav_offset(scr_reg)
        if res:
            return True
        else:
            return False

    def interdiction_check(self) -> bool:
        """ Checks if we are being interdicted or were already interdicted (dropped to normal space).
        Handles escape: submit, boost, SC engage. Returns True if interdiction was handled.
        """
        being_interdicted = self.status.get_flag(FlagsBeingInterdicted)
        # Only check journal flag if we're no longer in supercruise (already dumped to normal space)
        already_interdicted = (self.jn.ship_state()['interdicted']
                               and not self.status.get_flag(FlagsSupercruise))

        if not being_interdicted and not already_interdicted:
            return False

        logger.info("Danger. Interdiction detected.")
        self.ap_ckb('log', 'Interdiction detected.')

        # Submit if still in supercruise
        while self.status.get_flag(FlagsSupercruise) or self.status.get_flag2(Flags2FsdHyperdriveCharging):
            self.check_stop()
            self.set_speed_0()
            sleep(0.5)

        # In normal space now -- boost away and escape
        self.set_speed_100()

        # Wait for FSD cooldown to start
        self.status.wait_for_flag_on(FlagsFsdCooldown)

        # Boost while waiting for cooldown to complete
        while not self.status.wait_for_flag_off(FlagsFsdCooldown, timeout=1):
            self.check_stop()
            self.keys.send('UseBoostJuice')

        # Back to supercruise
        self.sc_engage()

        self.jn.ship_state()['interdicted'] = False
        return True

    def _capture_compass(self, scr_reg):
        """Capture compass region and prepare images for detection.
        Returns (compass_bgr, compass_hsv, orange_mask, comp_w, comp_h) or None on failure.
        """
        compass_image = scr_reg.capture_region(self.scr, 'compass')
        if compass_image is None:
            return None

        # 2x upscale for sub-pixel centroid accuracy (~0.75 deg instead of ~1.5 deg)
        compass_image = cv2.resize(compass_image, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        comp_h, comp_w = compass_image.shape[:2]

        if compass_image.shape[2] == 4:
            compass_bgr = cv2.cvtColor(compass_image, cv2.COLOR_BGRA2BGR)
        else:
            compass_bgr = compass_image
        compass_hsv = cv2.cvtColor(compass_bgr, cv2.COLOR_BGR2HSV)

        # Orange compass ring mask (hue ~5-25, high saturation)
        orange_mask = cv2.inRange(compass_hsv, (5, 100, 100), (25, 255, 255))

        return compass_bgr, compass_hsv, orange_mask, comp_w, comp_h

    def _detect_ring_center(self, scr_reg, orange_mask, comp_w, comp_h):
        """Detect compass ring center via 3-of-5 vote with HoughCircles.
        Returns (ring_cx, ring_cy, ring_r).
        """
        ring_r = 60.0  # Fixed: 30px real * 2x upscale
        valid_centers = []
        for _vote in range(5):
            if _vote > 0:
                sleep(0.01)
                cap = scr_reg.capture_region(self.scr, 'compass')
                cap = cv2.resize(cap, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
                if cap.shape[2] == 4:
                    cap_bgr = cv2.cvtColor(cap, cv2.COLOR_BGRA2BGR)
                else:
                    cap_bgr = cap
                cap_hsv = cv2.cvtColor(cap_bgr, cv2.COLOR_BGR2HSV)
                omask = cv2.inRange(cap_hsv, (5, 100, 100), (25, 255, 255))
            else:
                omask = orange_mask  # reuse first capture
            oblur = cv2.GaussianBlur(omask, (5, 5), 1)
            circles = cv2.HoughCircles(oblur, cv2.HOUGH_GRADIENT, dp=1.2,
                                       minDist=comp_w // 2,
                                       param1=50, param2=20,
                                       minRadius=comp_w // 5,
                                       maxRadius=comp_w // 2)
            if circles is not None:
                best = min(circles[0], key=lambda c: (c[0] - comp_w/2)**2 + (c[1] - comp_h/2)**2)
                dx = abs(best[0] - comp_w/2)
                dy = abs(best[1] - comp_h/2)
                if best[2] >= 55 and dx < 15 and dy < 15:
                    valid_centers.append((float(best[0]), float(best[1]), float(best[2])))

        ring_cx = comp_w / 2.0
        ring_cy = comp_h / 2.0
        if len(valid_centers) >= 3:
            valid_centers.sort(key=lambda c: c[0])
            ring_cx = valid_centers[len(valid_centers) // 2][0]
            valid_centers.sort(key=lambda c: c[1])
            ring_cy = valid_centers[len(valid_centers) // 2][1]
            avg_r = sum(c[2] for c in valid_centers) / len(valid_centers)
            logger.debug(f"Ring: center=({ring_cx:.1f},{ring_cy:.1f}) avg_r={avg_r:.1f} votes={len(valid_centers)}/5")
        else:
            logger.debug(f"Ring: {len(valid_centers)}/5 valid, using ROI center ({ring_cx:.0f},{ring_cy:.0f})")

        return ring_cx, ring_cy, ring_r

    def _detect_nav_dot(self, compass_hsv, orange_mask, comp_w, comp_h):
        """Detect cyan nav dot in compass image.
        Returns (dot_cx, dot_cy, z, front_mask, valid_contours) where z=1.0 if found, 0.0 if behind.
        """
        front_mask = cv2.inRange(compass_hsv, (75, 40, 170), (105, 255, 255))
        front_mask = cv2.bitwise_and(front_mask, cv2.bitwise_not(orange_mask))

        contours, _ = cv2.findContours(front_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_areas = [cv2.contourArea(c) for c in contours]
        valid = [c for c in contours if 2 < cv2.contourArea(c) < comp_w * comp_h * 0.3]

        if valid:
            largest = max(valid, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            M = cv2.moments(largest)
            if M["m00"] > 0:
                dot_cx = M["m10"] / M["m00"]
                dot_cy = M["m01"] / M["m00"]
                logger.debug(f"Dot: pos=({dot_cx:.1f},{dot_cy:.1f}) area={area:.1f} comp={comp_w}x{comp_h} contours={len(contours)} valid={len(valid)}")
                return dot_cx, dot_cy, 1.0, front_mask, valid

        logger.debug(f"Dot: BEHIND comp={comp_w}x{comp_h} contours={len(contours)} areas={all_areas[:5]}")
        return 0.0, 0.0, 0.0, front_mask, valid

    def _calc_nav_angles(self, dot_cx, dot_cy, ring_cx, ring_cy, ring_r, z):
        """Calculate roll/pitch/yaw angles from dot position relative to ring center.
        Returns offset dict {'x', 'y', 'z', 'roll', 'pit', 'yaw'}.
        """
        # Dot offset from ring center, normalized to ring radius
        x_pct = (dot_cx - ring_cx) / ring_r - self._nav_cor_x
        x_pct = max(min(x_pct, 1.0), -1.0)

        y_pct = -(dot_cy - ring_cy) / ring_r - self._nav_cor_y  # flip Y (screen Y is inverted)
        y_pct = max(min(y_pct, 1.0), -1.0)

        # Roll: 0 deg at 12 o'clock, clockwise positive
        roll_deg = 0.0
        if x_pct > 0.0:
            roll_deg = 90 - degrees(atan(y_pct / x_pct))
        elif x_pct < 0.0:
            roll_deg = -90 - degrees(atan(y_pct / x_pct))
        elif y_pct < 0.0:
            roll_deg = 180.0

        # Spherical angle mapping: navball is orthographic projection, position = sin(angle)
        cx = max(-1.0, min(1.0, x_pct))
        cy = max(-1.0, min(1.0, y_pct))
        if z > 0:
            pit_deg = degrees(asin(cy))
            yaw_deg = degrees(asin(cx))
        else:
            pit_deg = (180.0 - degrees(asin(cy))) if cy > 0 else (-180.0 - degrees(asin(cy)))
            yaw_deg = (180.0 - degrees(asin(cx))) if cx > 0 else (-180.0 - degrees(asin(cx)))

        return {'x': round(x_pct, 4), 'y': round(y_pct, 4), 'z': round(z, 2),
                'roll': round(roll_deg, 2), 'pit': round(pit_deg, 2), 'yaw': round(yaw_deg, 2)}

    def _save_compass_debug(self, compass_bgr, front_mask, valid_contours,
                            dot_cx, dot_cy, ring_cx, ring_cy, comp_w, comp_h, z, result):
        """Save compass detection debug images when DEBUG_COMPASS is enabled."""
        if not self.DEBUG_COMPASS:
            return
        dbg_dir = 'lab/compass_debug'
        os.makedirs(dbg_dir, exist_ok=True)
        _seq = getattr(self, '_dbg_compass_seq', 0)
        self._dbg_compass_seq = _seq + 1
        z_str = 'F' if z > 0 else 'B'
        tag = f"{_seq:03d}_p{result['pit']:+05.1f}_y{result['yaw']:+05.1f}_{z_str}"
        cv2.imwrite(f'{dbg_dir}/{tag}_compass.png', compass_bgr)
        cv2.imwrite(f'{dbg_dir}/{tag}_cyan.png', front_mask)
        annotated = compass_bgr.copy()
        cv2.drawContours(annotated, valid_contours, -1, (0, 255, 0), 1)
        if z > 0:
            cv2.drawMarker(annotated, (int(dot_cx), int(dot_cy)), (0, 0, 255), cv2.MARKER_CROSS, 8, 1)
        cv2.drawMarker(annotated, (comp_w // 2, comp_h // 2), (0, 255, 255), cv2.MARKER_CROSS, 8, 1)
        cv2.drawMarker(annotated, (int(ring_cx), int(ring_cy)), (255, 0, 0), cv2.MARKER_TILTED_CROSS, 10, 1)
        cv2.imwrite(f'{dbg_dir}/{tag}_annotated.png', annotated)

    def get_nav_offset(self, scr_reg, disable_auto_cal: bool = False):
        """ Determine the x,y offset from center of the compass of the nav point.
        @return: {'x': x.xx, 'y': y.yy, 'z': -1|0|+1, 'roll': r.rr, 'pit': p.pp, 'yaw': y.yy} | None
        """
        capture = self._capture_compass(scr_reg)
        if capture is None:
            return None
        compass_bgr, compass_hsv, orange_mask, comp_w, comp_h = capture

        ring_cx, ring_cy, ring_r = self._detect_ring_center(scr_reg, orange_mask, comp_w, comp_h)

        dot_cx, dot_cy, z, front_mask, valid_contours = self._detect_nav_dot(
            compass_hsv, orange_mask, comp_w, comp_h)

        if z == 0.0:
            return {'x': 0, 'y': 0, 'z': -1, 'roll': 180.0, 'pit': 180.0, 'yaw': 0}

        result = self._calc_nav_angles(dot_cx, dot_cy, ring_cx, ring_cy, ring_r, z)

        self._save_compass_debug(compass_bgr, front_mask, valid_contours,
                                 dot_cx, dot_cy, ring_cx, ring_cy, comp_w, comp_h, z, result)

        return result

    def is_sc_assist_gone(self, scr_reg) -> bool:
        """3-of-3 check whether SC Assist has actually disappeared.
        Uses the blue indicator check region only.
        @return: True if SC Assist is confirmed gone (all 3 checks fail).
        """
        gone_count = 0
        for i in range(self.VOTE_COUNT):
            sleep(3)

            mask = scr_reg.capture_region_filtered(self.scr, 'sc_assist_ind')

            ind_ratio = 0.0
            if mask is not None:
                mask_2x = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
                blue_count = cv2.countNonZero(mask_2x)
                blue_total = mask_2x.shape[0] * mask_2x.shape[1]
                ind_ratio = blue_count / blue_total if blue_total > 0 else 0

            logger.debug(f"sc_assist {i+1}/{self.VOTE_COUNT}: ratio={ind_ratio:.3f}")

            if ind_ratio < self.SC_ASSIST_GONE_RATIO:
                gone_count += 1
        if gone_count >= self.VOTE_COUNT:
            logger.info(f"is_sc_assist_gone: confirmed gone ({gone_count}/{self.VOTE_COUNT} checks)")
            return True
        logger.debug(f"is_sc_assist_gone: still active ({gone_count}/{self.VOTE_COUNT} gone)")
        return False

    # Target circle radius bounds at 1920x1080
    TARGET_CIRCLE_R_MIN = 44
    TARGET_CIRCLE_R_MAX = 48

    def _find_target_circle(self, image_bgr):
        """Find the orange target circle in an image using HoughCircles.
        HoughCircles detects circular arcs directly, ignoring nearby text.
        @return: (center_x, center_y) or None if no orange circle found.
        """
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

        # Orange filter for target circle
        orange_mask = cv2.inRange(hsv, np.array([16, 165, 220]), np.array([98, 255, 255]))
        blurred = cv2.GaussianBlur(orange_mask, (5, 5), 1)

        img_h, img_w = image_bgr.shape[:2]

        if self.DEBUG_TARGET_CIRCLE:
            orange_px = int(cv2.countNonZero(orange_mask))
            logger.info(f"[TGT_CIRCLE] image={img_w}x{img_h} orange_px={orange_px} r_range=[{self.TARGET_CIRCLE_R_MIN},{self.TARGET_CIRCLE_R_MAX}]")

        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2,
                                   minDist=img_w // 2,
                                   param1=50, param2=20,
                                   minRadius=self.TARGET_CIRCLE_R_MIN,
                                   maxRadius=self.TARGET_CIRCLE_R_MAX)

        if circles is None:
            if self.DEBUG_TARGET_CIRCLE:
                logger.info("[TGT_CIRCLE] no circle found")
            return None

        if self.DEBUG_TARGET_CIRCLE:
            for i, c in enumerate(circles[0]):
                dist = ((c[0] - img_w/2)**2 + (c[1] - img_h/2)**2)**0.5
                logger.info(f"[TGT_CIRCLE] candidate {i}: center=({c[0]:.0f},{c[1]:.0f}) r={c[2]:.0f} dist_from_center={dist:.0f}")

        # Pick the circle closest to image center
        best = min(circles[0], key=lambda c: (c[0] - img_w/2)**2 + (c[1] - img_h/2)**2)
        cx, cy, r = float(best[0]), float(best[1]), float(best[2])

        if self.DEBUG_TARGET_CIRCLE:
            logger.info(f"[TGT_CIRCLE] selected: center=({cx:.0f},{cy:.0f}) r={r:.0f}")

        return cx, cy

    def get_target_offset(self, scr_reg, disable_auto_cal: bool = False):
        """ Determine how far off we are from the target being in the middle of the screen.
        Uses color-based circle detection (no templates).
        @return: {'roll': r.rr, 'pit': p.pp, 'yaw': y.yy}, where all are in degrees
        """
        # Grab the target search region (center of screen)
        # scr_reg.reg rects are already in pixels (converted at Screen_Regions init)
        target_rect = scr_reg.reg['target']['rect']
        image = self.scr.get_screen_region(target_rect)
        if image is None:
            return None

        result_circle = self._find_target_circle(image)
        if result_circle is None:
            logger.debug("get_target_offset: no target circle found")
            return None

        cx, cy = result_circle
        img_h, img_w = image.shape[:2]

        # Convert circle center to screen-relative position
        # Region rect is [L, T, R, B] in pixels, convert to pct for position calc
        sw = self.scr.screen_width
        sh = self.scr.screen_height
        region_left_pct = target_rect[0] / sw
        region_top_pct = target_rect[1] / sh
        region_w_pct = (target_rect[2] - target_rect[0]) / sw
        region_h_pct = (target_rect[3] - target_rect[1]) / sh

        # Circle position as pct of full screen
        screen_x_pct = region_left_pct + (cx / img_w) * region_w_pct
        screen_y_pct = region_top_pct + (cy / img_h) * region_h_pct

        # Convert to -100..+100 range (0 = center of screen)
        final_x_pct = (screen_x_pct - 0.5) * 200.0
        final_y_pct = -(screen_y_pct - 0.5) * 200.0  # flip Y (up is positive)
        final_x_pct = max(min(final_x_pct, 100.0), -100.0)
        final_y_pct = max(min(final_y_pct, 100.0), -100.0)

        # Convert to degrees using FOV
        final_yaw_deg = final_x_pct / 100 * (self.hor_fov / 2)
        final_pit_deg = final_y_pct / 100 * (self.ver_fov / 2)

        # Calc roll angle (clock position of target)
        final_roll_deg = 0.0
        if final_x_pct > 0.0:
            final_roll_deg = 90 - degrees(atan(final_pit_deg / final_yaw_deg))
        elif final_x_pct < 0.0:
            final_roll_deg = -90 - degrees(atan(final_pit_deg / final_yaw_deg))
        elif final_y_pct < 0.0:
            final_roll_deg = 180.0

        logger.debug(f"get_target_offset: pit={final_pit_deg:.2f} yaw={final_yaw_deg:.2f}")

        result = {'roll': round(final_roll_deg, 2), 'pit': round(final_pit_deg, 2),
                  'yaw': round(final_yaw_deg, 2)}
        return result

    def undock(self):
        """ Performs menu action to undock from Station """
        MenuNav.undock(self.keys, self.status)
        self.set_speed_0(repeat=2)

        # Performs left menu ops to request docking

    def request_docking(self):
        """ Request docking from Nav Panel. """
        self.nav_panel.request_docking()

    def dock(self):
        """ Docking sequence. Boost toward station, request docking, let autodock handle it.
        Perform Refueling and Repair once docked.
        """
        # Wait for normal space after SC drop
        if self.jn.ship_state()['status'] != "in_space":
            sleep(2)
        if self.jn.ship_state()['status'] != "in_space":
            self.set_speed_0()
            logger.error('In dock(), still not in_space after wait')
            raise Exception('Docking failed (not in space)')

        # Boost toward station then pitch up to clear construction geometry
        self.keys.send('UseBoostJuice')
        sleep(self.BOOST_SETTLE)

        self._debug_snap(self.scrReg, 'approach')

        # Roll off the strut plane for rotating stations (Coriolis/Orbis/Ocellus)
        # Construction sites have no rotating struts, skip roll there
        drop_type = self.jn.ship_state().get('SupercruiseDestinationDrop_type') or ''
        if 'Construction' not in drop_type:
            roll_time = 30.0 / self.rollrate
            self.keys.send('RollRightButton', hold=roll_time)

        # Pitch up to clear station, then fly clear at full speed
        pitch_time = 65.0 / self.pitchrate
        self.keys.send('PitchUpButton', hold=pitch_time)
        self.set_speed_100()
        sleep(self.BOOST_SETTLE)

        self.set_speed_0()
        self.ap_ckb('log+vce', "Initiating Docking Procedure")
        self.request_docking()
        sleep(1.5)  # journal catch-up

        if self.jn.ship_state()['status'] == "dockingdenied":
            self.ap_ckb('log', 'Docking denied, retrying in 30s...')
            logger.warning('Docking denied: '+str(self.jn.ship_state()['no_dock_reason']))
            sleep(30)
            self.request_docking()
            sleep(1.5)
            if self.jn.ship_state()['status'] != "dockinggranted":
                self.ap_ckb('log', 'Docking denied again: '+str(self.jn.ship_state()['no_dock_reason']))
                raise Exception('Docking failed (denied twice)')

        self.ap_ckb('log+vce', "Docking request granted")
        # Wait for autodock to complete -- check journal for docked status
        for i in range(self.config['WaitForAutoDockTimer']):
            self.check_stop()
            if self.jn.ship_state()['status'] == "in_station":
                sleep(2)  # settle before continuing
                MenuNav.refuel_repair_rearm(self.keys, self.status)
                return True
            sleep(2)

        self.ap_ckb('log+vce', 'Auto dock timer timed out.')
        logger.warning('Auto dock timer timed out. Aborting Docking.')
        return False

    def is_sun_dead_ahead(self, scr_reg):
        return scr_reg.sun_percent(scr_reg.screen) > 5

    # use to orient the ship to not be pointing right at the Sun
    # Checks brightness in the region in front of us, if brightness exceeds a threshold
    # then will pitch up until below threshold.
    #
    def sun_avoid(self, scr_reg):
        """Pitch up away from sun if it's ahead. Returns True if sun avoidance was needed.
        Strategy: 25% throttle, 45deg initial pull-up, 15deg steps until clear,
        15deg safety reserve, 100% pass, then 15deg pitch down to recover heading."""
        logger.debug('align= avoid sun')

        if not self.is_sun_dead_ahead(scr_reg):
            return False

        self.set_speed_25()

        # Failsafe: don't pitch more than 120deg total
        fail_safe_timeout = (120 / self.pitchrate) + 3
        starttime = time.time()

        # Step 1: Initial 45deg pull-up to get away from sun fast
        initial_time = 45.0 / self.pitchrate
        logger.info(f"Sun ahead, initial pull-up {initial_time:.1f}s (45deg)")
        self.keys.send('PitchUpButton', hold=initial_time)

        # Keep pitching in 15deg steps until sun is clear
        step_time = 15.0 / self.pitchrate
        while self.is_sun_dead_ahead(scr_reg):
            logger.info(f"Sun still ahead, pitching up {step_time:.1f}s (15deg)")
            self.keys.send('PitchUpButton', hold=step_time)
            if (time.time() - starttime) > fail_safe_timeout:
                logger.debug('sun avoid failsafe timeout')
                break

        # Step 2: Extra 15deg safety pitch up
        reserve_time = 15.0 / self.pitchrate
        logger.info(f"Sun clear, reserve pitch up {reserve_time:.1f}s (15deg safety)")
        self.keys.send('PitchUpButton', hold=reserve_time)

        # Full speed for fly-by (position() handles the 30s pass)
        self.set_speed_100()

        return True

    # Delegate steering helpers to Ship (kept as thin wrappers for caller compat)

    @staticmethod
    def _roll_on_centerline(roll_deg, close):
        return Ship._roll_on_centerline(roll_deg, close)

    def _align_axis(self, scr_reg, axis, off, close=10.0, timeout=None):
        return self.ship.align_axis(scr_reg, axis, off, close, timeout, get_offset_fn=self.get_nav_offset)

    def _roll_to_centerline(self, scr_reg, off, close=10.0):
        return self.ship.roll_to_centerline(scr_reg, off, close, get_offset_fn=self.get_nav_offset)

    def _yaw_to_center(self, scr_reg, off, close=10.0):
        return self.ship.yaw_to_center(scr_reg, off, close, get_offset_fn=self.get_nav_offset)

    def _pitch_to_center(self, scr_reg, off, close=10.0):
        return self.ship.pitch_to_center(scr_reg, off, close, get_offset_fn=self.get_nav_offset)

    def _avg_offset(self, scr_reg, get_offset_fn):
        return self.ship.avg_offset(scr_reg, get_offset_fn)

    # Constants proxied from Ship for callers that reference self.ALIGN_CLOSE etc.
    ROLE_YAW_PITCH_CLOSE = Ship.ROLE_YAW_PITCH_CLOSE
    ROLE_TRESHHOLD = Ship.ROLE_TRESHHOLD
    MIN_HOLD_TIME = Ship.MIN_HOLD_TIME
    MAX_HOLD_TIME = Ship.MAX_HOLD_TIME
    ALIGN_CLOSE = Ship.ALIGN_CLOSE
    ALIGN_SETTLE = Ship.ALIGN_SETTLE
    ALIGN_TIMEOUT = Ship.ALIGN_TIMEOUT
    # SC Assist detection
    SC_ASSIST_GONE_RATIO = 0.50 # cyan ratio below this = indicator gone
    SC_ASSIST_CHECK_INTERVAL = 3   # seconds between gone checks
    SC_SETTLE_TIME = 5          # seconds to let SC assist settle after engage
    # Evasion pitch angles and cruise time
    OCCLUSION_PITCH = 65
    BODY_EVADE_PITCH = 90
    PASSBODY_TIME = 25
    # Common angles
    QUARTER_TURN = 90           # 90-degree pitch maneuvers
    # Key input settle time for navigation commands
    KEY_WAIT = 0.125
    # Dock approach
    DOCK_PRE_PITCH = 1.0        # seconds pitch up before boost toward station
    BOOST_SETTLE = 4            # seconds wait after boost for speed to stabilize
    UNDOCK_SETTLE = 5           # seconds wait during undock sequences
    # Voting
    VOTE_COUNT = 3              # 3-of-3 consensus checks
    # Debug
    DEBUG_SNAP = False           # save debug snapshots to debug-output/
    DEBUG_COMPASS = False        # save compass detection images to lab/compass_debug/
    DEBUG_TARGET_CIRCLE = True   # verbose logging for target circle detection

    def _debug_snap(self, scr_reg, label):
        """Save a debug snapshot if DEBUG_SNAP is enabled."""
        if not self.DEBUG_SNAP:
            return
        try:
            snap = scr_reg.capture_region(self.scr, 'center_normalcruise')
            if snap is not None:
                snap_dir = os.path.join('debug-output', 'target-snap')
                os.makedirs(snap_dir, exist_ok=True)
                ts = time.strftime('%Y%m%d_%H%M%S')
                cv2.imwrite(os.path.join(snap_dir, f'{label}_{ts}.png'), snap)
                logger.info(f"Debug snapshot saved: {label}_{ts}.png")
        except Exception as e:
            logger.warning(f"Debug snapshot failed: {e}")

    def _evade_pitch(self, scr_reg, pitch_degrees):
        """Pitch up to evade, cruise, then re-align and re-engage SC Assist."""
        self.keys.send('SetSpeed25')
        pitch_time = pitch_degrees / self.pitchrate
        self.keys.send('PitchUpButton', hold=pitch_time)
        self.set_speed_100()
        sleep(self.PASSBODY_TIME)
        self.set_speed_0()
        self.compass_align(scr_reg)
        self.keys.send('SetSpeed75')
        sleep(self.SC_SETTLE_TIME)

    def compass_align(self, scr_reg) -> bool:
        """ Align ship to compass nav target.
        Strategy:
          1) If target behind: pitch UP to flip (away from star)
          2) If roll > 45deg off centerline: coarse roll to get close
          3) Yaw + Pitch for fine alignment (reliable, no overshoot)
        @return: True if aligned, else False.
        """
        close = self.ALIGN_CLOSE
        # Use status.json flags (reliable) instead of journal status (can be stale from corrupt lines)
        in_sc = self.status.get_flag(FlagsSupercruise)
        in_space = not self.status.get_flag(FlagsDocked) and not self.status.get_flag(FlagsLanded)
        if not (in_sc or in_space):
            logger.error(f'align=err1, not in super or space. journal={self.jn.ship_state()["status"]}')
            raise Exception('nav_align not in super or space')

        self.ap_ckb('log+vce', 'Compass Align')
        self.set_speed_0()
        prev_off = None
        self._flip_count = 0

        align_tries = 0
        max_align_tries = self.config['NavAlignTries']
        max_total_loops = max_align_tries * 5  # safety cap to prevent infinite loop

        for loop in range(max_total_loops):
            self.check_stop()
            if self.interdiction_check():
                self.ap_ckb('log', 'Interdicted during align, restarting...')
                self.set_speed_25()
                prev_off = None
                continue

            off = self.get_nav_offset(scr_reg)
            if off is None:
                self.ap_ckb('log', 'Unable to detect compass. Rolling to new position.')
                self.roll_clockwise_anticlockwise(90)
                prev_off = None
                continue  # no-compass doesn't count as alignment try

            logger.debug(f"Compass: roll={off['roll']:.1f} pit={off['pit']:.1f} yaw={off['yaw']:.1f} z={off['z']}")

            # Target behind -- pitch UP in 90° steps with compass check between each
            # Sequence: 90°, 90°, 90°, 45° (max 4 attempts)
            if off['z'] < 0:
                flip_count = getattr(self, '_flip_count', 0)
                effective_rate = self.pitchrate * self.ZERO_THROTTLE_RATE_FACTOR
                if flip_count < 3:
                    flip_deg = 90.0
                elif flip_count == 3:
                    flip_deg = 45.0
                    logger.warning("Compass: 3x 90deg flips failed, trying 45deg")
                else:
                    logger.error("Compass: 4 flips exhausted, giving up")
                    break
                pitch_time = flip_deg / effective_rate
                logger.info(f"Compass: target behind, flip {flip_count+1}/4 pitch {flip_deg:.0f}deg ({pitch_time:.1f}s)")
                self.ap_ckb('log', 'Target behind, flipping up')
                self.keys.send('PitchUpButton', hold=pitch_time)
                sleep(self.ALIGN_SETTLE)
                self._flip_count = flip_count + 1
                prev_off = off
                continue
            prev_off = off

            # Already aligned?
            if abs(off['pit']) < close and abs(off['yaw']) < close:
                self.ap_ckb('log', 'Compass Align complete')
                return True

            # Coarse roll to vertical centerline when dot is diagonal AND far enough from center
            roll_off_centerline = min(abs(off['roll']), 180 - abs(off['roll']))
            if abs(off['yaw']) > self.ROLE_TRESHHOLD and roll_off_centerline > self.ROLE_YAW_PITCH_CLOSE:
                logger.info(f"Compass: roll {roll_off_centerline:.1f}deg off centerline, coarse roll")
                self.ap_ckb('log', 'Coarse roll')
                off = self._roll_to_centerline(scr_reg, off, close=self.ROLE_YAW_PITCH_CLOSE)
                if off is None:
                    continue
                if off.get('z', 1) < 0:
                    effective_rate = self.pitchrate * self.ZERO_THROTTLE_RATE_FACTOR
                    pitch_time = 90.0 / effective_rate
                    logger.info(f"Compass: target went behind during roll, pitching 90deg ({pitch_time:.1f}s)")
                    self.keys.send('PitchUpButton', hold=pitch_time)
                    sleep(0.5)
                    continue

            # Fine alignment -- THIS counts as an alignment try
            # Do the larger-offset axis first: when pitch is large, the dot is near
            # the circle edge where yaw has reduced effectiveness (spherical projection).
            # Pitching first brings the dot closer to center so yaw becomes effective.
            align_tries += 1
            logger.info(f"Compass: alignment attempt {align_tries}/{max_align_tries}")

            if abs(off['pit']) > abs(off['yaw']):
                off = self._pitch_to_center(scr_reg, off, close)
                if off is None:
                    continue
                off = self._yaw_to_center(scr_reg, off, close)
                if off is None:
                    continue
            else:
                off = self._yaw_to_center(scr_reg, off, close)
                if off is None:
                    continue
                off = self._pitch_to_center(scr_reg, off, close)
                if off is None:
                    continue

            # Verify alignment with 3-of-3 avg to filter navball jitter
            med = self._avg_offset(scr_reg, self.get_nav_offset)
            if med is not None:
                logger.info(f"Compass after align: avg pit={med['pit']:.1f} yaw={med['yaw']:.1f}")
            if med is not None and abs(med['pit']) < close and abs(med['yaw']) < close:
                self.ap_ckb('log', 'Compass Align complete')
                return True

            # Verify failed -- alignment was applied, accept anyway
            # (compass jitter ~3-4deg can cause verify to fail even when close)
            self.ap_ckb('log', 'Compass Align complete')
            return True

        self.ap_ckb('log+vce', 'Compass Align failed - exhausted all retries')
        return False

    def mnvr_to_target(self, scr_reg):
        """ Maneuver to Target using compass then target before performing a jump."""
        logger.debug('mnvr_to_target entered')

        if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
            logger.error('align() not in sc or space')
            raise Exception('align() not in sc or space')

        sun_was_ahead = self.sun_avoid(scr_reg)

        res = self.compass_align(scr_reg)

        # Aligned -- start FSD charge now (after align to avoid drift)
        logger.info('mnvr_to_target: compass align done, starting FSD')
        self.ap_ckb('log', 'Compass aligned, starting FSD')
        self.keys.send('HyperSuperCombination')
        self.set_speed_100()

    # position() happens after a refuel and performs
    #   - accelerate past sun
    #   - perform Discovery scan
    def position(self, scr_reg, sun_was_ahead=False):
        logger.debug('position')

        self.set_speed_100()

        logger.info("Passing star with SCO boost")

        # SCO burst to quickly clear the star instead of 30s crawl
        self.keys.send('UseBoostJuice')
        sleep(4.5)
        self.keys.send('UseBoostJuice')  # disable SCO

        logger.info("Maneuvering")

        # Pitch down to recover heading while SCO momentum decays
        if sun_was_ahead:
            recover_time = 15.0 / self.pitchrate
            logger.info(f"Post fly-by, pitching down {recover_time:.1f}s (15deg recovery)")
            self.keys.send('PitchDownButton', hold=recover_time)

        self.set_speed_0()

        logger.debug('position=complete')
        return True

    def jump(self, scr_reg):
        logger.debug('jump')

        logger.info("Frameshift Jump")

        # FSD already pulled us into jump during align -- just wait for completion
        if self.status.get_flag(FlagsFsdJump):
            logger.info('jump: already in FSD jump (pulled in during align)')
            res = self.status.wait_for_flag_off(FlagsFsdJump, 360)
            if not res:
                logger.error('FSD failure to complete jump timeout.')
                raise Exception('FSD jump timeout')
            self.jump_cnt = self.jump_cnt + 1
            self.set_speed_0(repeat=3)
            return

        jump_tries = self.config['JumpTries']
        for i in range(jump_tries):
            self.check_stop()
            logger.debug('jump= try:'+str(i))

            # FSD already charging from compass_align -- skip straight to wait
            if not (self.status.get_flag(FlagsFsdCharging) or self.status.get_flag(FlagsFsdJump)):
                self.keys.send('HyperSuperCombination')
                res = self.status.wait_for_flag_on(FlagsFsdCharging, 5)
                if not res:
                    logger.error('FSD failed to charge.')
                    continue

            res = self.status.wait_for_flag_on(FlagsFsdJump, 60)
            if not res:
                # FSD still charged? Alignment drifted -- let FSD retry or drop charge
                if self.status.get_flag(FlagsFsdCharging):
                    logger.info("jump: FSD charged but no jump -- waiting for pull-in or charge drop")
                    continue
                # Charge dropped -- full realign needed
                logger.warning('FSD failure to start jump timeout.')
                self.mnvr_to_target(scr_reg)
                continue

            logger.debug('jump= in jump')
            # Wait for jump to complete. Should never err
            res = self.status.wait_for_flag_off(FlagsFsdJump, 360)
            if not res:
                logger.error('FSD failure to complete jump timeout.')
                continue

            logger.debug('jump= speed 0')
            self.jump_cnt = self.jump_cnt+1
            self.set_speed_0(repeat=3)  # Let's be triply sure that we set speed to 0% :)
            sleep(1)  # wait 1 sec after jump to allow graphics to stablize and accept inputs
            logger.debug('jump=complete')

            # We completed the jump
            return True

        logger.error(f'FSD Jump failed {jump_tries} times. jump=err2')
        raise Exception("FSD Jump failure")

    def roll_clockwise_anticlockwise(self, deg):
        self.ship.roll_clockwise_anticlockwise(deg)

    def pitch_up_down(self, deg):
        self.ship.pitch_up_down(deg)

    def yaw_right_left(self, deg):
        self.ship.yaw_right_left(deg)

    def waypoint_undock_seq(self):
        self.update_ap_status("Executing Undocking/Launch")

        # Store current location (on planet or in space)
        on_planet = self.status.get_flag(FlagsHasLatLong)
        station_type = self.jn.ship_state()['exp_station_type']
        logger.info(f"Undock: exp_station_type={station_type}, station={self.jn.ship_state()['cur_station']}")
        starport = station_type == EDJournal.StationType.Starport

        # Leave starport or planetary port
        if not on_planet:
            # Check that we are docked
            if self.status.get_flag(FlagsDocked):
                # Check if we have an advanced docking computer
                if not self.jn.ship_state()['has_adv_dock_comp']:
                    self.ap_ckb('log', "Unable to undock. Advanced Docking Computer not fitted.")
                    logger.warning('Unable to undock. Advanced Docking Computer not fitted.')
                    raise Exception('Unable to undock. Advanced Docking Computer not fitted.')

                # Undock from station
                self.undock()

                if starport:
                    # Starports have mail slots -- wait for autodock to clear via journal
                    # Music: DockingComputer -> NoTrack means autodock finished, we're outside
                    logger.info("Starport undock: waiting for Music:NoTrack journal event")
                    for i in range(48):
                        self.check_stop()
                        self.jn.ship_state()
                        track = self.jn.ship.get('music_track', '')
                        if track == 'NoTrack':
                            logger.info(f"Starport undock: Music:NoTrack after {(i+1)*5}s -- mail slot cleared")
                            break
                        logger.debug(f"Starport undock: music_track='{track}', waiting...")
                        sleep(self.UNDOCK_SETTLE)
                    else:
                        logger.warning("Starport undock: 240s timeout waiting for NoTrack, proceeding anyway")
                    self.set_speed_100()
                else:
                    # All non-starport stations: brief wait, then pitch away, boost, clear
                    sleep(self.UNDOCK_SETTLE)
                    self.ap_ckb('log+vce', 'Maneuvering away from station')
                    self.set_speed_50()
                    pitch_time = self.config['OCDepartureAngle'] / self.pitchrate
                    self.keys.send('PitchUpButton', hold=pitch_time)
                    self.keys.send('UseBoostJuice')
                    sleep(self.BOOST_SETTLE)

                self.update_ap_status("Undock Complete, accelerating")
                self.sc_engage()

        elif on_planet:
            # Check if we are on a landing pad (docked), or landed on the planet surface
            if self.status.get_flag(FlagsDocked):
                # We are on a landing pad (docked)
                # Check if we have an advanced docking computer
                if not self.jn.ship_state()['has_adv_dock_comp']:
                    self.ap_ckb('log', "Unable to undock. Advanced Docking Computer not fitted.")
                    logger.warning('Unable to undock. Advanced Docking Computer not fitted.')
                    raise Exception('Unable to undock. Advanced Docking Computer not fitted.')

                # Undock from port
                self.undock()
                sleep(self.UNDOCK_SETTLE)

            elif self.status.get_flag(FlagsLanded):
                # We are on planet surface (not docked at planet landing pad)
                self.keys.send('UpThrustButton', hold=6)
                self.keys.send('LandingGearToggle')

            # Leave planet: pitch up, boost, engage SC (no pitch back on planet)
            self.ap_ckb('log+vce', 'Maneuvering away from planet')
            self.set_speed_50()
            pitch_time = self.config['OCDepartureAngle'] / self.pitchrate
            self.keys.send('PitchUpButton', hold=pitch_time)
            self.keys.send('UseBoostJuice')
            sleep(self.BOOST_SETTLE)
            self.update_ap_status("Undock Complete, accelerating")
            self.sc_engage()

            # Wait until out of orbit.
            res = self.status.wait_for_flag_off(FlagsHasLatLong, timeout=60)

            # Disable SCO. If SCO not fitted, this will do nothing.
            self.keys.send('UseBoostJuice')

    def wait_masslock_clear(self, max_checks=10):
        """Boost and wait until masslock clears. Boosts once per check cycle."""
        if not self.status.get_flag(FlagsFsdMassLocked):
            return
        self.ap_ckb('log', 'Waiting for masslock to clear...')
        self.set_speed_100()
        for _ in range(max_checks):
            if not self.status.get_flag(FlagsFsdMassLocked):
                break
            self.keys.send('UseBoostJuice')
            sleep(self.UNDOCK_SETTLE)

    def sc_engage(self) -> bool:
        """ Engages supercruise. Clears masslock first (boosting), then SC.
        """
        if self.status.get_flag(FlagsSupercruise):
            return True

        for attempt in range(3):
            self.check_stop()
            if self._game_lost():
                raise Exception('sc_engage: game lost')
            self.set_speed_100()
            self.wait_masslock_clear()
            self.keys.send('Supercruise')

            res = self.status.wait_for_flag_on(FlagsSupercruise, timeout=20)
            if res:
                return True
            logger.warning(f'sc_engage: not in supercruise after 20s (attempt {attempt+1})')

        raise Exception('sc_engage: failed after 3 attempts')

    def waypoint_assist(self, keys, scr_reg):
        """ Processes the waypoints, performing jumps and sc assist if going to a station
        also can then perform trades if specific in the waypoints file."""
        self.waypoint.waypoint_assist(keys, scr_reg)

    def do_route_jump(self, scr_reg):
        """Single FSD jump: sun avoid, align, jump, fly away from star.
        Used by waypoint loop which handles multi-jump routes one jump at a time."""
        self.update_ap_status("Align")
        self.mnvr_to_target(scr_reg)

        self.update_ap_status("Jump")
        self.jump(scr_reg)

        # Update jump counters
        self.total_dist_jumped += self.jn.ship_state()['dist_jumped']
        self.total_jumps = self.jump_cnt + self.jn.ship_state()['jumps_remains']
        self.jn.ship_state()['jumps_remains'] = 0

        # Sun avoidance
        sun_was_ahead = self.sun_avoid(scr_reg)

        self.update_ap_status("Maneuvering")
        self.position(scr_reg, sun_was_ahead=sun_was_ahead)

    def supercruise_to_station(self, scr_reg, station_name: str) -> bool:
        """ Supercruise to the specified target, which may be a station, FC, body, signal source, etc.
        Returns True if we travel successfully travel there, else False. """
        # If waypoint file has a Station Name associated then attempt targeting it
        self.update_ap_status(f"Targeting Station: {station_name}")

        # if we are starting the waypoint docked at a station, we need to undock first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage()

        # Lock target in SC -- target was set in galmap while docked, K re-locks it in SC
        sleep(3)
        self.keys.send('TargetNextRouteSystem')
        sleep(2)

        if self.have_destination(scr_reg):
            self.ap_ckb('log', " - Station: " + station_name)
            self.update_ap_status(f"SC to Station: {station_name}")
            self.sc_assist(scr_reg)
        else:
            self.ap_ckb('log', f" - Could not target station: {station_name}")
            return False

        return True

    def sc_assist(self, scr_reg, do_docking=True):
        """ Supercruise Assist: sun avoid, align to target, activate SC Assist via nav panel,
        then monitor for auto-drop. Checks for body obscuring target every 2.5s.
        """
        logger.debug("Entered sc_assist")

        # Goto cockpit view
        self.ship_control.goto_cockpit_view()

        # see if we have a compass up, if so then we have a target
        if not self.have_destination(scr_reg):
            self.ap_ckb('log', "Quiting SC Assist - Compass not found. Rotate ship and try again.")
            logger.debug("Quiting sc_assist - compass not found")
            return

        # if we are starting the waypoint docked at a station or landed, we need to undock/takeoff first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):

            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage()
        self.jn.ship_state()['interdicted'] = False

        # Verify we are actually in supercruise before proceeding (use status.json flag,
        # journal status can be stale if FSDJump line was corrupted during read)
        if not self.status.get_flag(FlagsSupercruise):
            self.ap_ckb('log', 'SC Assist aborted - not in supercruise')
            logger.warning(f"sc_assist: not in supercruise (flag), journal status={self.jn.ship_state()['status']}")
            return

        # Activate SC Assist first, then align -- SC Assist guides while we fine-tune
        self.set_speed_0()
        sleep(0.5)
        self.ap_ckb('log', 'Activating SC Assist via Nav Panel')
        if not self.nav_panel.activate_sc_assist():
            self.ap_ckb('log', 'SC Assist activation failed, retrying...')
            sleep(2)
            if not self.nav_panel.activate_sc_assist():
                self.ap_ckb('log', 'SC Assist activation failed twice, aborting')
                logger.warning("sc_assist: activate_sc_assist failed after retry")
                self.set_speed_0()
                return

        # Sun avoidance (pitch up if sun ahead after FSD drop)
        sun_was_ahead = self.sun_avoid(scr_reg)

        # Check if close enough to let SC Assist pull while we fine-tune
        off = self.get_nav_offset(scr_reg)
        if off and abs(off['pit']) < 10 and abs(off['yaw']) < 10:
            logger.info(f"sc_assist: close enough (pit={off['pit']:.1f} yaw={off['yaw']:.1f}), throttle up for pull")
            self.keys.send('SetSpeed75')

        # Align to target using compass
        aligned = self.compass_align(scr_reg)
        if not aligned:
            self.ap_ckb('log', 'SC Assist: compass align failed, retrying once...')
            sleep(2)
            aligned = self.compass_align(scr_reg)

        # Throttle up -- SC Assist is active and we're aligned (or close enough)
        self.keys.send('SetSpeed75')
        sc_assist_cruising = False  # wait for throttle text to clear first

        # Wait for SC Assist to fly us there and drop us out
        self.ap_ckb('log', 'Waiting for SC Assist to reach destination...')
        sleep(self.SC_SETTLE_TIME)  # let SC Assist settle and throttle text disappear
        sc_assist_cruising = True
        last_align_check = time.time()
        while True:
            sleep(2.5)
            self.check_stop()

            if not self.status.get_flag(FlagsSupercruise):
                # Dropped from supercruise (SC Assist completed or glide)
                if self.status.get_flag2(Flags2GlideMode):
                    logger.debug("Gliding")
                    self.status.wait_for_flag2_off(Flags2GlideMode, 30)
                else:
                    logger.debug("No longer in supercruise - SC Assist dropped us")

                self._debug_snap(scr_reg, 'drop')

                break

            # Body proximity check -- ApproachBody journal event
            approach_body = self.jn.ship_state().get('approach_body')
            if approach_body:
                self.jn.ship['approach_body'] = None  # clear so we don't re-trigger
                sc_assist_cruising = False
                self.ap_ckb('log+vce', f'Approaching body: {approach_body} -- evading')
                logger.info(f"sc_assist: ApproachBody detected: {approach_body}")
                self._evade_pitch(scr_reg, self.BODY_EVADE_PITCH)
                sc_assist_cruising = True
                continue

            # Check if SC Assist is still active (indicator check)
            # If gone: target is occluded, evade by pitching up and re-aligning
            if sc_assist_cruising and (time.time() - last_align_check) > self.SC_ASSIST_CHECK_INTERVAL:
                last_align_check = time.time()
                if self.is_sc_assist_gone(scr_reg):
                    # SC may have dropped during the ~4.5s check -- normal arrival, not occlusion
                    if not self.status.get_flag(FlagsSupercruise):
                        logger.info("sc_assist: indicator gone but SC already dropped -- normal arrival")
                        break
                    # Interdiction kills the indicator too -- let the interdiction handler deal with it
                    if self.status.get_flag(FlagsBeingInterdicted):
                        logger.info("sc_assist: indicator gone due to interdiction -- skipping evasion")
                        sc_assist_cruising = False
                        continue
                    logger.warning("sc_assist: gone -- target occluded, evading")
                    self.ap_ckb('log', 'Target occluded -- evading')
                    sc_assist_cruising = False
                    self._evade_pitch(scr_reg, self.OCCLUSION_PITCH)
                    sc_assist_cruising = True
                    last_align_check = time.time()
                    continue

            # check if we are being interdicted
            interdicted = self.interdiction_check()
            if interdicted:
                # After interdiction, re-align and re-activate SC Assist
                self.set_speed_50()
                self.compass_align(scr_reg)
                self.nav_panel.activate_sc_assist()

        # We've dropped from supercruise
        if do_docking:
            sleep(1)  # wait for the journal to catch up

            # Check if this is a target we cannot dock at
            skip_docking = False
            if not self.jn.ship_state()['has_adv_dock_comp'] and not self.jn.ship_state()['has_std_dock_comp']:
                self.ap_ckb('log', "Skipping docking. No Docking Computer fitted.")
                skip_docking = True

            if not self.jn.ship_state()['SupercruiseDestinationDrop_type'] is None:
                if (self.jn.ship_state()['SupercruiseDestinationDrop_type'].startswith("$USS_Type")
                        # Bulk Cruisers
                        or "-class Cropper" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Hauler" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Reformatory" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Researcher" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Surveyor" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Traveller" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Tanker" in self.jn.ship_state()['SupercruiseDestinationDrop_type']):
                    self.ap_ckb('log', "Skipping docking. No docking privilege at MegaShips.")
                    skip_docking = True

            if not skip_docking:
                # go into docking sequence
                docked_ok = self.dock()
                if not docked_ok:
                    stype = self.jn.ship_state().get('exp_station_type')
                    if stype in (EDJournal.StationType.SpaceConstructionDepot,
                                 EDJournal.StationType.ColonisationShip):
                        self.ap_ckb('log+vce', "Docking failed at construction site -- stopping navigation")
                        return
                    self.ap_ckb('log', "Docking timed out, continuing...")
                if docked_ok:
                    self.ap_ckb('log+vce', "Docking complete, refueled, repaired and re-armed")
                    self.update_ap_status("Docking Complete")
            else:
                self.set_speed_0()
        else:
            logger.info("Exiting Supercruise, setting throttle to zero")
            self.set_speed_0()  # make sure we don't continue to land
            self.ap_ckb('log', "Supercruise dropped, terminating SC Assist")

        self.ap_ckb('log+vce', "Supercruise Assist complete")

    def dss_assist(self):
        while True:
            sleep(0.5)
            self.check_stop()
            if self.jn.ship_state()['status'] == 'in_supercruise':
                cur_star_system = self.jn.ship_state()['cur_star_system']
                if cur_star_system != self._prev_star_system:
                    self.update_ap_status("DSS Scan")
                    self.ap_ckb('log', 'DSS Scan: '+cur_star_system)
                    set_focus_elite_window()
                    self._prev_star_system = cur_star_system
                    self.update_ap_status("Idle")

    # raising an exception to the engine loop thread, so we can terminate its execution
    #  if thread was in a sleep, the exception seems to not be delivered
    def check_stop(self):
        """Check if stop was requested and raise EDAP_Interrupt if so.
        Call this at the top of main loop iterations for safe interrupt points."""
        if self._stop_event.is_set():
            raise EDAP_Interrupt

    #
    # Setter routines for state variables
    #
    def _game_lost(self) -> bool:
        """Check if game window is gone or at main menu. Stops all assists if so."""
        window_gone = not Screen.Screen.elite_window_exists()
        at_menu = self.jn.ship_state().get('music_track') == 'MainMenu'
        if window_gone or at_menu:
            reason = "window gone" if window_gone else "main menu"
            logger.error(f"Game lost ({reason}) -- stopping all assists")
            self.ap_ckb('log', f"ERROR: Game lost ({reason}). Stopping all assists.")
            self.sc_assist_enabled = False
            self.waypoint_assist_enabled = False
            self.dss_assist_enabled = False
            return True
        return False

    def set_sc_assist(self, enable=True):
        if not enable and self.sc_assist_enabled:
            self._stop_event.set()
        self.sc_assist_enabled = enable

    def set_waypoint_assist(self, enable=True):
        if not enable and self.waypoint_assist_enabled:
            self._stop_event.set()
        self.waypoint_assist_enabled = enable

    def set_dss_assist(self, enable=True):
        if not enable and self.dss_assist_enabled:
            self._stop_event.set()
        self.dss_assist_enabled = enable

    def set_activate_elite_eachkey(self, enable=False):
        self.config["ActivateEliteEachKey"] = enable

    def set_automatic_logout(self, enable=False):
        self.config["AutomaticLogout"] = enable

    def set_log_error(self, enable=False):
        self.config["LogDEBUG"] = False
        self.config["LogINFO"] = False
        logger.setLevel(logging.ERROR)

    def set_log_debug(self, enable=False):
        self.config["LogDEBUG"] = True
        self.config["LogINFO"] = False
        logger.setLevel(logging.DEBUG)

    def set_log_info(self, enable=False):
        self.config["LogDEBUG"] = False
        self.config["LogINFO"] = True
        logger.setLevel(logging.INFO)

    # quit() is important to call to clean up, if we don't terminate the threads we created the AP will hang on exit
    # have then then kill python exec
    def quit(self):
        self.terminate = True

    #
    # This function will execute in its own thread and will loop forever until
    # the self.terminate flag is set
    #
    def _run_assist(self, name, func, *args):
        """Run an assist function with standard error handling.
        Returns True if _game_lost() was detected (caller should continue loop).
        """
        self._stop_event.clear()
        set_focus_elite_window()
        try:
            func(*args)
        except EDAP_Interrupt:
            logger.debug(f"Caught stop exception in {name}")
        except Exception as e:
            logger.exception(f"{name} trapped generic")
            if self._game_lost():
                return True
        return False

    def calibrate_rates(self, mode):
        """Delegate calibration to Ship."""
        self.ship.calibrate_rates(mode, self.scrReg, self.get_nav_offset)

    def engine_loop(self):
        while not self.terminate:
            # Guard: require loaded screen regions before any autopilot action
            if not self.scrReg.regions_loaded and (
                self.sc_assist_enabled or self.waypoint_assist_enabled
            ):
                w = self.scrReg.screen.screen_width
                h = self.scrReg.screen.screen_height
                msg = f"No screen region config found for resolution {w}x{h}. Cannot start autopilot."
                logger.error(msg)
                self.ap_ckb('log', msg)
                self.sc_assist_enabled = False
                self.waypoint_assist_enabled = False
                self.ap_ckb('sc_stop')
                self.ap_ckb('waypoint_stop')

            if self.sc_assist_enabled == True:
                logger.debug("Running sc_assist")
                self.update_ap_status("SC to Target")
                if self._run_assist("SC Assist", self.sc_assist, self.scrReg):
                    continue
                logger.debug("Completed sc_assist")
                if not self.sc_assist_enabled:
                    self.ap_ckb('sc_stop')
    

            elif self.waypoint_assist_enabled == True:
                logger.debug("Running waypoint_assist")
                self.jump_cnt = 0
                self.refuel_cnt = 0
                self.total_dist_jumped = 0
                self.total_jumps = 0
                if self._run_assist("Waypoint Assist", self.waypoint_assist, self.keys, self.scrReg):
                    continue
                if not self.waypoint_assist_enabled:
                    self.ap_ckb('waypoint_stop')
    

            elif self.dss_assist_enabled == True:
                logger.debug("Running dss_assist")
                if self._run_assist("DSS Assist", self.dss_assist):
                    continue
                self.dss_assist_enabled = False
                self.ap_ckb('dss_stop')

            elif self.calibrate_normal_enabled:
                logger.debug("Running calibration: normal space")
                if self._run_assist("Calibrate Normal", self.calibrate_rates, 'normal'):
                    continue
                self.calibrate_normal_enabled = False

            elif self.calibrate_sc_enabled:
                logger.debug("Running calibration: SC 0% throttle")
                if self._run_assist("Calibrate SC", self.calibrate_rates, 'sc_zero'):
                    continue
                self.calibrate_sc_enabled = False

            # Check once EDAPGUI loaded to prevent errors logging to the listbox before loaded
            if self.gui_loaded:
                # Check if ship has changed
                ship = self.jn.ship_state()['type']
                # Check if a ship and not a suit (on foot)
                if ship not in ship_size_map:
                    self.ship.ship_type = ''
                else:
                    old_type = self.ship.ship_type
                    switched = self.ship.update_ship_type(ship)
                    ship_fullname = EDJournal.get_ship_fullname(ship)

                    if old_type is None:
                        # First detection
                        self.ap_ckb('log+vce', f"Welcome aboard your {ship_fullname}.")
                    elif switched:
                        cur_ship_fullname = EDJournal.get_ship_fullname(old_type)
                        self.ap_ckb('log+vce', f"Switched ship from your {cur_ship_fullname} to your {ship_fullname}.")

                    if old_type != ship:
                        # Check for fuel scoop and advanced docking computer
                        if not self.jn.ship_state()['has_fuel_scoop']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with a Fuel Scoop.")
                        if not self.jn.ship_state()['has_adv_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with an Advanced Docking Computer.")
                        if self.jn.ship_state()['has_std_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is fitted with a Standard Docking Computer.")

                        # Update GUI with ship config
                        self.ap_ckb('update_ship_cfg')



            cv2.waitKey(10)
            sleep(1)

    def set_speed_0(self, repeat=1):
        self.ship.set_speed_0(repeat)

    def set_speed_25(self, repeat=1):
        self.ship.set_speed_25(repeat)

    def set_speed_50(self, repeat=1):
        self.ship.set_speed_50(repeat)

    def set_speed_100(self, repeat=1):
        self.ship.set_speed_100(repeat)

