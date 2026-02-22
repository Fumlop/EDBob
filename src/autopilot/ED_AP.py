import json
import math
import os
import threading
import time
from copy import copy
from datetime import datetime, timedelta
from time import sleep
from enum import Enum
from math import asin, atan, degrees
import random
from string import Formatter
from tkinter import messagebox

import cv2
import numpy as np
import kthread
from simple_localization import LocalizationManager


from src.autopilot.EDAP_EDMesg_Server import EDMesgServer
from src.core.EDAP_data import (
    FlagsDocked, FlagsLanded, FlagsLandingGearDown, FlagsSupercruise, FlagsFsdMassLocked,
    FlagsFsdCharging, FlagsFsdCooldown, FlagsFsdJump,
    FlagsHasLatLong, FlagsBeingInterdicted,
    FlagsAnalysisMode, Flags2FsdHyperdriveCharging,
    Flags2GlideMode, GuiFocusNoFocus, ship_size_map, ship_rpy_sc_50,
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
from src.screen.OCR import OCR
from src.ed.EDNavigationPanel import EDNavigationPanel
from src.screen.Overlay import Overlay
from src.ed.StatusParser import StatusParser


def read_json_file(filepath: str):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding='utf-8') as fp:
            return json.load(fp)
    except Exception as e:
        logger.warning(f"read_json_file error for '{filepath}': {e}")
        return None


def write_json_file(data, filepath: str):
    if not os.path.exists(filepath) or data is None:
        return False
    try:
        with open(filepath, "w", encoding='utf-8') as fp:
            json.dump(data, fp, indent=4)
            return True
    except Exception as e:
        logger.warning(f"write_json_file error for '{filepath}': {e}")
        return False


"""
File:EDAP.py    EDAutopilot

Description:

Note:
Ideas taken from: https://github.com/skai2/EDAutopilot

Author: sumzer0@yahoo.com
"""


# Exception class used to unroll the call tree to to stop execution
class EDAP_Interrupt(Exception):
    pass


class ScTargetAlignReturn(Enum):
    Lost = 1
    Found = 2
    Disengage = 3


def scale(inp: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """ Does scaling of the input based on input and output min/max."""
    return (inp - in_min)/(in_max - in_min) * (out_max - out_min) + out_min


class EDAutopilot:

    _AXIS_CONFIG = {
        'pitch': {'rate_attr': 'pitchrate', 'lookup_key': 'PitchRate',
                  'threshold': 30, 'pos_key': 'PitchUpButton', 'neg_key': 'PitchDownButton'},
        'roll':  {'rate_attr': 'rollrate',  'lookup_key': 'RollRate',
                  'threshold': 45, 'pos_key': 'RollRightButton', 'neg_key': 'RollLeftButton'},
        'yaw':   {'rate_attr': 'yawrate',   'lookup_key': 'YawRate',
                  'threshold': 30, 'pos_key': 'YawRightButton', 'neg_key': 'YawLeftButton'},
    }

    def __init__(self, cb, doThread=True):
        self.config = {}
        self.ship_configs = {
            "Ship_Configs": {},  # Dictionary of ship types with additional settings
        }
        self._prev_star_system = None
        self.speed_demand = None
        self._ocr = None
        self.ship_tst_roll_enabled = False
        self.ship_tst_pitch_enabled = False
        self.ship_tst_yaw_enabled = False

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
        self._stop_event = threading.Event()  # safe interrupt signal for assist threads

        # Create instance of each of the needed Classes
        self.scr = Screen.Screen(cb)
        self.scr.scaleX = self.config['ScreenScale']
        self.scr.scaleY = self.config['ScreenScale']

        self.gfx_settings = EDGraphicsSettings()
        # Aspect ratio greater than 1920/1080 (1.7777) seems to be the magic cutoff. At > 1920/1080 (1.7777), the FOV
        # appears to be the top of the screen. Looks like FDev made the FOV for 1920x1080 resolution height.
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

        self.mesg_server = EDMesgServer(self, cb)
        self.mesg_server.actions_port = self.config['EDMesgActionsPort']
        self.mesg_server.events_port = self.config['EDMesgEventsPort']
        if self.config['EnableEDMesg']:
            self.mesg_server.start_server()

        # Set defaults for data read from ships config
        self.yawrate   = 8.0
        self.rollrate  = 80.0
        self.pitchrate = 33.0
        self.sunpitchuptime = 0.0
        self.yawfactor = 0.0
        self.rollfactor = 0.0
        self.pitchfactor = 0.0

        self.ap_ckb = cb

        self.load_ship_configs()

        self.jump_cnt = 0
        self._eta = 0
        self._str_eta = ''
        self.total_dist_jumped = 0
        self.total_jumps = 0
        self.refuel_cnt = 0
        self.current_ship_type = None
        self.gui_loaded = False
        self._nav_cor_x = 0.0  # Nav Point correction to pitch
        self._nav_cor_y = 0.0  # Nav Point correction to yaw
        self.target_align_outer_lim = 1.0  # In deg. Anything outside of this range will cause alignment.
        self.target_align_inner_lim = 0.5  # In deg. Will stop alignment when in this range.
        self.debug_show_compass_overlay = False
        self.debug_show_target_overlay = False

        # Overlay vars
        self.ap_state = "Idle"
        # Initialize the Overlay class
        self.overlay = Overlay("", elite=1)
        self.overlay.overlay_setfont(self.config['OverlayTextFont'], self.config['OverlayTextFontSize'])
        self.overlay.overlay_set_pos(self.config['OverlayTextXOffset'], self.config['OverlayTextYOffset'])
        # must be called after we initialized the objects above
        self.update_overlay()

        self.debug_overlay = False
        self.debug_ocr = False
        self.debug_images = False
        self.debug_image_folder = './debug-output/images'
        if not os.path.exists(self.debug_image_folder):
            os.makedirs(self.debug_image_folder)

        # debug window
        self.cv_view = False
        self.cv_view_x = 10
        self.cv_view_y = 10

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

    @property
    def ocr(self) -> OCR:
        """ Load OCR class when needed. """
        if not self._ocr:
            self._ocr = OCR(self, self.scr)
        return self._ocr

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
            "EnableRandomness": False,  # add some additional random sleep times to avoid AP detection (0-3sec at specific locations)
            "ActivateEliteEachKey": False,  # Activate Elite window before each key or group of keys
            "OverlayTextEnable": False,  # Experimental at this stage
            "OverlayTextYOffset": 400,  # offset down the screen to start place overlay text
            "OverlayTextXOffset": 50,  # offset left the screen to start place overlay text
            "OverlayTextFont": "Eurostyle",
            "OverlayTextFontSize": 14,
            "OverlayGraphicEnable": False,  # not implemented yet
            "DiscordWebhook": False,  # discord not implemented yet
            "DiscordWebhookURL": "",
            "DiscordUserID": "",
            "LogDEBUG": False,  # enable for debug messages
            "LogINFO": True,
            "Enable_CV_View": 0,  # Should CV View be enabled by default
            "ShipConfigFile": None,  # Ship config to load on start - deprecated
            "TargetScale": 1.0,  # Scaling of the target when a system is selected
            "ScreenScale": 1.0,  # Scaling of the target when a system is selected
            "AutomaticLogout": False,  # Logout when we are done with the mission
            "OCDepartureAngle": 75.0,  # Angle to pitch up when departing non-starport stations
            "Language": 'en',  # Language (matching ./locales/xx.json file)
            "OCRLanguage": 'en',  # Language for OCR detection (see OCR language doc in \docs)
            "EnableEDMesg": False,
            "EDMesgActionsPort": 15570,
            "EDMesgEventsPort": 15571,
            "DebugOverlay": False,
            "HotkeysEnable": False,  # Enable hotkeys
            "WaypointFilepath": "",  # The previous waypoint file path
            "DebugOCR": False,  # For debug, write all OCR data to output folder
            "DebugImages": False,  # For debug, write debug images to output folder
            "Key_ModDelay": 0.01,  # Delay for key modifiers to ensure modifier is detected before/after the key
            "Key_DefHoldTime": 0.2,  # Default hold time for a key press
            "Key_RepeatDelay": 0.1,  # Delay between key press repeats
            "DisengageUseMatch": False,  # For 'Disengage' use old image match instead of OCR
            "target_align_outer_lim": 1.0,  # For test
            "target_align_inner_lim": 0.5,  # For test
            "Debug_ShowCompassOverlay": False,  # For test
            "Debug_ShowTargetOverlay": False,  # For test
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
        shp_cnf = read_json_file(filepath='./configs/ship_configs.json')

        # if we read it then point to it, otherwise use the default table above
        if shp_cnf is not None:
            if len(shp_cnf) != len(self.ship_configs):
                # If configs of different lengths, then a new parameter was added.
                # self.write_config(self.config)
                # Add default values for new entries
                if 'Ship_Configs' not in shp_cnf:
                    shp_cnf['Ship_Configs'] = dict()
                self.ship_configs = shp_cnf
                logger.debug("read Ships Config json:" + str(shp_cnf))
            else:
                self.ship_configs = shp_cnf
                logger.debug("read Ships Config json:" + str(shp_cnf))
        else:
            write_json_file(self.ship_configs, filepath='./configs/ship_configs.json')

        # Load ship configuration with proper hierarchy
        if self.jn:
            ship = self.jn.ship_state()['type']
            if ship:
                self.load_ship_configuration(ship)

    def update_ship_configs(self):
        """ Update the user's ship configuration file."""
        # Check if a ship and not a suit (on foot)
        if self.current_ship_type in ship_size_map:
            # Ensure ship entry exists in config
            if self.current_ship_type not in self.ship_configs['Ship_Configs']:
                self.ship_configs['Ship_Configs'][self.current_ship_type] = {}
                logger.debug(f"Created new ship config entry for: {self.current_ship_type}")
            
            self.ship_configs['Ship_Configs'][self.current_ship_type]['PitchRate'] = self.pitchrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['RollRate'] = self.rollrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['YawRate'] = self.yawrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['SunPitchUp+Time'] = self.sunpitchuptime
            self.ship_configs['Ship_Configs'][self.current_ship_type]['PitchFactor'] = self.pitchfactor
            self.ship_configs['Ship_Configs'][self.current_ship_type]['RollFactor'] = self.rollfactor
            self.ship_configs['Ship_Configs'][self.current_ship_type]['YawFactor'] = self.yawfactor

            write_json_file(self.ship_configs, filepath='./configs/ship_configs.json')
            logger.debug(f"Saved ship config for: {self.current_ship_type}")

    def load_ship_configuration(self, ship_type):
        """ Load ship configuration with the following priority:
            1. User's ship values from ship_configs.json file
            2. Default ship values from default_ships_cfg_sc_50.json file
            3. Hardcoded default values
        """
        self.ap_ckb('log', f"Loading ship configuration for your {ship_type}")

        # Step 1: Use hardcoded defaults
        self.rollrate = 80.0
        self.pitchrate = 33.0
        self.yawrate = 8.0
        self.sunpitchuptime = 0.0
        self.rollfactor = 20.0
        self.pitchfactor = 12.0
        self.yawfactor = 12.0
        logger.info(f"Loaded hardcoded default configuration for {ship_type}")

        # Step 2: Try to load defaults from ship file
        if ship_type in ship_rpy_sc_50:
            ship_defaults = ship_rpy_sc_50[ship_type]
            # Use default configuration - this means it's been modified and saved to ship_configs.json
            self.rollrate = ship_defaults.get('RollRate', 80.0)
            self.pitchrate = ship_defaults.get('PitchRate', 33.0)
            self.yawrate = ship_defaults.get('YawRate', 8.0)
            self.sunpitchuptime = ship_defaults.get('SunPitchUp+Time', 0.0)
            logger.info(f"Loaded default configuration for {ship_type} from default ship cfg file")

        # Step 3: Check if we have custom config in ship_configs.json (skip if forcing defaults)
        if ship_type in self.ship_configs['Ship_Configs']:
            current_ship_cfg = self.ship_configs['Ship_Configs'][ship_type]
            # Check if the custom config has actual values (not just empty dict)
            if any(key in current_ship_cfg for key in ['RollRate', 'PitchRate', 'YawRate', 'SunPitchUp+Time']):
                # Use custom configuration - this means it's been modified and saved to ship_configs.json
                self.rollrate = current_ship_cfg.get('RollRate', 80.0)
                self.pitchrate = current_ship_cfg.get('PitchRate', 33.0)
                self.yawrate = current_ship_cfg.get('YawRate', 8.0)
                self.sunpitchuptime = current_ship_cfg.get('SunPitchUp+Time', 0.0)
                logger.info(f"Loaded your custom configuration for {ship_type} from ship_configs.json")

            if any(key in current_ship_cfg for key in ['RollFactor', 'PitchFactor', 'YawFactor']):
                # Use custom configuration - this means it's been modified and saved to ship_configs.json
                self.rollfactor = current_ship_cfg.get('RollFactor', 20.0)
                self.pitchfactor = current_ship_cfg.get('PitchFactor', 12.0)
                self.yawfactor = current_ship_cfg.get('YawFactor', 12.0)
                # return

            # Check RPY Calibration
            spd_dmd = 'SCSpeed50'
            if spd_dmd not in current_ship_cfg:
                self.ap_ckb('log', "WARNING: Perform Roll/Pitch/Yaw Calibration on this ship.")
            else:
                speed_demand = current_ship_cfg[spd_dmd]
                if 'RollRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Roll Calibration on this ship.")
                if 'PitchRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Pitch Calibration on this ship.")
                if 'YawRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Yaw Calibration on this ship.")

        # Add empty entry to ship_configs for future customization
        if ship_type not in self.ship_configs['Ship_Configs']:
            self.ship_configs['Ship_Configs'][ship_type] = dict()

    def update_overlay(self):
        """ Draw the overlay data on the ED Window """
        if self.config['OverlayTextEnable']:
            ap_mode = "Offline"
            if self.sc_assist_enabled:
                ap_mode = "SC Assist"
            elif self.waypoint_assist_enabled:
                ap_mode = "Waypoint Assist"
            elif self.dss_assist_enabled:
                ap_mode = "DSS Assist"

            ship_state = self.jn.ship_state()['status']
            if ship_state is None:
                ship_state = '<init>'

            sclass = self.jn.ship_state()['star_class']
            if sclass is None:
                sclass = "<init>"

            location = self.jn.ship_state()['location']
            if location is None:
                location = "<init>"
            self.overlay.overlay_text('1', "AP MODE: "+ap_mode, 1, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('2', "AP STATUS: "+self.ap_state, 2, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('3', "SHIP STATUS: "+ship_state, 3, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('4', "CURRENT SYSTEM: "+location+", "+sclass, 4, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('5', "JUMPS: {} of {}".format(self.jump_cnt, self.total_jumps), 5, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('6', "ETA (to System): "+self._str_eta, 6, 1, (136, 53, 0), -1)
            self.overlay.overlay_paint()

    def update_ap_status(self, txt):
        self.ap_state = txt
        self.update_overlay()
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

        self.cv_view = self.config['Enable_CV_View']
        self.debug_show_compass_overlay = self.config['Debug_ShowCompassOverlay']
        self.debug_show_target_overlay = self.config['Debug_ShowTargetOverlay']
        self.debug_overlay = self.config['DebugOverlay']
        self.debug_ocr = self.config['DebugOCR']
        self.debug_images = self.config['DebugImages']

    def draw_match_rect(self, img, pt1, pt2, color, thick):
        """ Draws the matching rectangle within the image. """
        wid = pt2[0]-pt1[0]
        hgt = pt2[1]-pt1[1]

        if wid < 20:
            #cv2.rectangle(screen, pt, (pt[0] + compass_width, pt[1] + compass_height),  (0,0,255), 2)
            cv2.rectangle(img, pt1, pt2, color, thick)
        else:
            len_wid = wid/5
            len_hgt = hgt/5
            half_wid = wid/2
            half_hgt = hgt/2
            tic_len = thick-1
            # top
            cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0]+len_wid), int(pt1[1])), color, thick)
            cv2.line(img, (int(pt1[0]+(2*len_wid)), int(pt1[1])), (int(pt1[0]+(3*len_wid)), int(pt1[1])), color, 1)
            cv2.line(img, (int(pt1[0]+(4*len_wid)), int(pt1[1])), (int(pt2[0]), int(pt1[1])), color, thick)
            # top tic
            cv2.line(img, (int(pt1[0]+half_wid), int(pt1[1])), (int(pt1[0]+half_wid), int(pt1[1])-tic_len), color, thick)
            # bot
            cv2.line(img, (int(pt1[0]), int(pt2[1])), (int(pt1[0]+len_wid), int(pt2[1])), color, thick)
            cv2.line(img, (int(pt1[0]+(2*len_wid)), int(pt2[1])), (int(pt1[0]+(3*len_wid)), int(pt2[1])), color, 1)
            cv2.line(img, (int(pt1[0]+(4*len_wid)), int(pt2[1])), (int(pt2[0]), int(pt2[1])), color, thick)
            # bot tic
            cv2.line(img, (int(pt1[0]+half_wid), int(pt2[1])), (int(pt1[0]+half_wid), int(pt2[1])+tic_len), color, thick)
            # left
            cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0]), int(pt1[1]+len_hgt)), color, thick)
            cv2.line(img, (int(pt1[0]), int(pt1[1]+(2*len_hgt))), (int(pt1[0]), int(pt1[1]+(3*len_hgt))), color, 1)
            cv2.line(img, (int(pt1[0]), int(pt1[1]+(4*len_hgt))), (int(pt1[0]), int(pt2[1])), color, thick)
            # left tic
            cv2.line(img, (int(pt1[0]), int(pt1[1]+half_hgt)), (int(pt1[0]-tic_len), int(pt1[1]+half_hgt)), color, thick)
            # right
            cv2.line(img, (int(pt2[0]), int(pt1[1])), (int(pt2[0]), int(pt1[1]+len_hgt)), color, thick)
            cv2.line(img, (int(pt2[0]), int(pt1[1]+(2*len_hgt))), (int(pt2[0]), int(pt1[1]+(3*len_hgt))), color, 1)
            cv2.line(img, (int(pt2[0]), int(pt1[1]+(4*len_hgt))), (int(pt2[0]), int(pt2[1])), color, thick)
            # right tic
            cv2.line(img, (int(pt2[0]), int(pt1[1]+half_hgt)), (int(pt2[0]+tic_len), int(pt1[1]+half_hgt)), color, thick)

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

    def get_nav_offset(self, scr_reg, disable_auto_cal: bool = False):
        """ Determine the x,y offset from center of the compass of the nav point.
        @return: {'x': x.xx, 'y': y.yy, 'z': -1|0|+1, 'roll': r.rr, 'pit': p.pp, 'yaw': y.yy} | None
        Where:
            'pit':  0 = dead ahead, +90 = top edge, -90 = bottom edge,
                    +180 = dead behind (over top), -180 = dead behind (under bottom)
            'roll': 0 = 12 o'clock, +180 = 6 o'clock clockwise, -180 = 6 o'clock anticlockwise
            'z':    +1 = target in front, -1 = target behind
        """
        import time as _time
        _t0 = _time.perf_counter()

        # Capture compass region directly (fixed bounding box from config)
        compass_image = scr_reg.capture_region(self.scr, 'compass', inv_col=False)

        c_left = scr_reg.reg['compass']['rect'][0]
        c_top = scr_reg.reg['compass']['rect'][1]

        _t1 = _time.perf_counter()

        # 2x upscale for sub-pixel centroid accuracy (~0.75 deg instead of ~1.5 deg)
        compass_image = cv2.resize(compass_image, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        comp_h, comp_w = compass_image.shape[:2]

        logger.debug(f"Compass capture: {comp_w}x{comp_h} (2x upscaled) capture={_t1-_t0:.3f}s")

        # Find nav dot by color instead of template matching
        # Convert to HSV for color-based detection
        if compass_image.shape[2] == 4:
            compass_bgr = cv2.cvtColor(compass_image, cv2.COLOR_BGRA2BGR)
        else:
            compass_bgr = compass_image
        compass_hsv = cv2.cvtColor(compass_bgr, cv2.COLOR_BGR2HSV)

        # Mask out the orange compass ring (hue ~5-25, high saturation)
        orange_mask = cv2.inRange(compass_hsv, (5, 100, 100), (25, 255, 255))

        # Detect compass ring center: 3-of-5 vote with HoughCircles
        # Take 5 captures, keep results with hough_r >= 55, use median if 3+ valid
        ring_r = 60.0  # Fixed: 30px real * 2x upscale
        valid_centers = []
        for _vote in range(5):
            if _vote > 0:
                sleep(0.01)
                cap = scr_reg.capture_region(self.scr, 'compass', inv_col=False)
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
                # Reject: radius too small OR center too far from ROI center
                dx = abs(best[0] - comp_w/2)
                dy = abs(best[1] - comp_h/2)
                if best[2] >= 55 and dx < 15 and dy < 15:
                    valid_centers.append((float(best[0]), float(best[1]), float(best[2])))

        ring_cx = comp_w / 2.0
        ring_cy = comp_h / 2.0
        if len(valid_centers) >= 3:
            # Median of valid centers
            valid_centers.sort(key=lambda c: c[0])
            ring_cx = valid_centers[len(valid_centers) // 2][0]
            valid_centers.sort(key=lambda c: c[1])
            ring_cy = valid_centers[len(valid_centers) // 2][1]
            avg_r = sum(c[2] for c in valid_centers) / len(valid_centers)
            logger.debug(f"Ring: center=({ring_cx:.1f},{ring_cy:.1f}) avg_r={avg_r:.1f} votes={len(valid_centers)}/5")
        else:
            logger.debug(f"Ring: {len(valid_centers)}/5 valid, using ROI center ({ring_cx:.0f},{ring_cy:.0f})")

        # Look for cyan dot (front target): hue ~75-105, val 170+
        # Front dot is cyan (hue~90, sat~80, val~204)
        front_mask = cv2.inRange(compass_hsv, (75, 40, 170), (105, 255, 255))
        front_mask = cv2.bitwise_and(front_mask, cv2.bitwise_not(orange_mask))

        # Try front dot by color
        final_z_pct = 0.0
        dot_cx, dot_cy = ring_cx, ring_cy  # default to ring center

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
                final_z_pct = 1.0
                _t3 = _time.perf_counter()
                logger.debug(f"Dot: pos=({dot_cx:.1f},{dot_cy:.1f}) area={area:.1f} comp={comp_w}x{comp_h} contours={len(contours)} valid={len(valid)} total={_t3-_t0:.3f}s")

        # Store debug data for saving after angle calc (so filename includes pit/yaw)
        _dbg_compass_bgr = compass_bgr
        _dbg_front_mask = front_mask
        _dbg_valid = valid
        _dbg_dot_cx = dot_cx
        _dbg_dot_cy = dot_cy
        _dbg_z = final_z_pct

        if final_z_pct == 0.0:
            # No cyan front dot = target is behind.
            _t3 = _time.perf_counter()
            logger.debug(f"Dot: BEHIND comp={comp_w}x{comp_h} contours={len(contours)} areas={all_areas[:5]} total={_t3-_t0:.3f}s")
            return {'x': 0, 'y': 0, 'z': -1, 'roll': 180.0, 'pit': 180.0, 'yaw': 0}

        # Convert dot position relative to detected ring center (-1.0 to 1.0)
        ring_radius = ring_r

        # Dot offset from ring center, normalized to ring radius
        final_x_pct = (dot_cx - ring_cx) / ring_radius
        final_x_pct = final_x_pct - self._nav_cor_x
        final_x_pct = max(min(final_x_pct, 1.0), -1.0)

        final_y_pct = -(dot_cy - ring_cy) / ring_radius  # flip Y (screen Y is inverted)
        final_y_pct = final_y_pct - self._nav_cor_y
        final_y_pct = max(min(final_y_pct, 1.0), -1.0)

        # Calc angle in degrees starting at 0 deg at 12 o'clock and increasing clockwise
        # so 3 o'clock is +90° and 9 o'clock is -90°.
        final_roll_deg = 0.0
        if final_x_pct > 0.0:
            final_roll_deg = 90 - degrees(atan(final_y_pct/final_x_pct))
        elif final_x_pct < 0.0:
            final_roll_deg = -90 - degrees(atan(final_y_pct/final_x_pct))
        elif final_y_pct < 0.0:
            final_roll_deg = 180.0

        # Spherical angle mapping: navball is a sphere rendered flat (orthographic projection)
        # dot position = sin(angle), so angle = asin(position)
        if final_z_pct > 0:
            # Front hemisphere: clamp to [-1,1] for asin safety
            clamped_y = max(-1.0, min(1.0, final_y_pct))
            clamped_x = max(-1.0, min(1.0, final_x_pct))
            final_pit_deg = degrees(asin(clamped_y))
            final_yaw_deg = degrees(asin(clamped_x))
        else:
            # Behind hemisphere
            clamped_y = max(-1.0, min(1.0, final_y_pct))
            clamped_x = max(-1.0, min(1.0, final_x_pct))
            if clamped_y > 0:
                final_pit_deg = 180.0 - degrees(asin(clamped_y))
            else:
                final_pit_deg = -180.0 - degrees(asin(clamped_y))
            if clamped_x > 0:
                final_yaw_deg = 180.0 - degrees(asin(clamped_x))
            else:
                final_yaw_deg = -180.0 - degrees(asin(clamped_x))

        result = {'x': round(final_x_pct, 4), 'y': round(final_y_pct, 4), 'z': round(final_z_pct, 2),
                  'roll': round(final_roll_deg, 2), 'pit': round(final_pit_deg, 2), 'yaw': round(final_yaw_deg, 2)}

        # Draw box around compass region
        if self.debug_overlay:
            border = 10
            c_right = scr_reg.reg['compass']['rect'][2]
            c_bottom = scr_reg.reg['compass']['rect'][3]

            self.overlay.overlay_rect('compass', (c_left - border, c_top - border), (c_right + border, c_bottom + border), (0, 255, 0), 2)
            self.overlay.overlay_floating_text('compass', f'Fixed region', c_left - border, c_top - border - 45, (0, 255, 0))
            self.overlay.overlay_floating_text('compass_rpy', f'r: {round(final_roll_deg, 2)} p: {round(final_pit_deg, 2)} y: {round(final_yaw_deg, 2)}', c_left - border, c_bottom + border, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            icompass_image_d = compass_image.copy()
            icompass_image_d = cv2.rectangle(icompass_image_d, (0, 0), (comp_w, 45), (0, 0, 0), -1)
            cv2.putText(icompass_image_d, f'x: {final_x_pct:5.2f} y: {final_y_pct:5.2f} z: {final_z_pct:5.2f}', (1, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'r: {final_roll_deg:5.2f}deg p: {final_pit_deg:5.2f}deg y: {final_yaw_deg:5.2f}deg', (1, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('compass', icompass_image_d)
            cv2.moveWindow('compass', self.cv_view_x - 400, self.cv_view_y + 600)
            cv2.waitKey(30)

        # Debug: save compass detection images with pit/yaw in filename
        if False:  # set True for navball calibration
            import os
            dbg_dir = 'lab/compass_debug'
            os.makedirs(dbg_dir, exist_ok=True)
            _seq = getattr(self, '_dbg_compass_seq', 0)
            self._dbg_compass_seq = _seq + 1
            z_str = 'F' if _dbg_z > 0 else 'B'
            tag = f"{_seq:03d}_p{final_pit_deg:+05.1f}_y{final_yaw_deg:+05.1f}_{z_str}"
            cv2.imwrite(f'{dbg_dir}/{tag}_compass.png', _dbg_compass_bgr)
            cv2.imwrite(f'{dbg_dir}/{tag}_cyan.png', _dbg_front_mask)
            annotated = _dbg_compass_bgr.copy()
            cv2.drawContours(annotated, _dbg_valid, -1, (0, 255, 0), 1)
            if _dbg_z > 0:
                cv2.drawMarker(annotated, (int(_dbg_dot_cx), int(_dbg_dot_cy)), (0, 0, 255), cv2.MARKER_CROSS, 8, 1)
            # Yellow + = ROI center, Cyan x = detected ring center
            cv2.drawMarker(annotated, (comp_w // 2, comp_h // 2), (0, 255, 255), cv2.MARKER_CROSS, 8, 1)
            cv2.drawMarker(annotated, (int(ring_cx), int(ring_cy)), (255, 0, 0), cv2.MARKER_TILTED_CROSS, 10, 1)
            cv2.imwrite(f'{dbg_dir}/{tag}_annotated.png', annotated)

        return result

    def is_target_arc_visible(self, scr_reg) -> bool:
        """Check if the orange target arc is visible near screen center.
        Detects partial arcs by checking that orange pixels lie at a consistent
        radius from screen center (960,540). Text has scattered distances (high std),
        arc pixels cluster at one radius (low std).
        @return: True if arc-like orange pattern is found (min 30px, radius std < 12).
        """
        if 'target_arc' not in scr_reg.reg:
            return False
        raw = scr_reg.capture_region(self.scr, 'target_arc', inv_col=False)
        if raw is None:
            return False
        hsv = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
        orange_mask = cv2.inRange(hsv, (16, 165, 220), (98, 255, 255))
        count = cv2.countNonZero(orange_mask)

        if count < self.MIN_ARC_PIXELS:
            logger.debug(f"target_arc: orange={count}px -- too few")
            return False

        # Check if orange pixels form an arc (consistent radius from screen center)
        box_x1 = scr_reg.reg['target_arc']['rect'][0]
        box_y1 = scr_reg.reg['target_arc']['rect'][1]
        ys, xs = np.where(orange_mask > 0)
        dists = np.sqrt((xs + box_x1 - 960)**2 + (ys + box_y1 - 540)**2)
        r_std = dists.std()
        r_mean = dists.mean()

        is_arc = r_std < self.ARC_STD_THRESHOLD
        logger.debug(f"target_arc: orange={count}px r_mean={r_mean:.1f} r_std={r_std:.1f} arc={is_arc}")
        return is_arc

    def target_fine_align(self, scr_reg) -> bool:
        """Use the on-screen target circle for precise fine alignment.
        The target circle center = exact target position. Screen center (960,540) = aligned.
        @return: True if fine alignment succeeded.
        """
        _dbg = self.DEBUG_TARGET_CIRCLE

        target_off = self.get_target_offset(scr_reg)
        if target_off is None:
            if _dbg:
                logger.info("[TGT_ALIGN] no target circle found, aborting")
            return False

        pit = target_off['pit']
        yaw = target_off['yaw']
        if _dbg:
            logger.info(f"[TGT_ALIGN] initial offset: pit={pit:.1f} yaw={yaw:.1f}")

        # Already close enough
        if abs(pit) < self.FINE_ALIGN_CLOSE and abs(yaw) < self.FINE_ALIGN_CLOSE:
            if _dbg:
                logger.info(f"[TGT_ALIGN] already aligned (threshold={self.FINE_ALIGN_CLOSE})")
            return True

        # Single correction per axis -- gentle, 50% approach
        if abs(pit) > 2.0:
            key = 'PitchUpButton' if pit > 0 else 'PitchDownButton'
            hold = (abs(pit) * 0.5) / self.pitchrate
            hold = max(0.10, min(1.0, hold))
            if _dbg:
                logger.info(f"[TGT_ALIGN] pitch correction: {pit:.1f}deg -> hold={hold:.2f}s key={key}")
            self.keys.send(key, hold=hold)
            sleep(2.0)

        if abs(yaw) > 2.0:
            # Re-read after pitch correction
            target_off = self.get_target_offset(scr_reg)
            if target_off is None:
                if _dbg:
                    logger.info("[TGT_ALIGN] lost target after pitch correction")
                return False
            yaw = target_off['yaw']
            if _dbg:
                logger.info(f"[TGT_ALIGN] post-pitch yaw={yaw:.1f}")
            if abs(yaw) > 2.0:
                key = 'YawRightButton' if yaw > 0 else 'YawLeftButton'
                hold = (abs(yaw) * 0.5) / self.yawrate
                hold = max(0.10, min(1.0, hold))
                if _dbg:
                    logger.info(f"[TGT_ALIGN] yaw correction: {yaw:.1f}deg -> hold={hold:.2f}s key={key}")
                self.keys.send(key, hold=hold)
                sleep(2.0)

        # Verify with 3-of-3 avg
        med = self._avg_offset(scr_reg, self.get_target_offset)
        if _dbg:
            if med:
                logger.info(f"[TGT_ALIGN] final avg: pit={med['pit']:.1f} yaw={med['yaw']:.1f} (ok_threshold={self.FINE_ALIGN_OK})")
            else:
                logger.info("[TGT_ALIGN] final avg: no valid readings")
        aligned = med is not None and abs(med['pit']) < self.FINE_ALIGN_OK and abs(med['yaw']) < self.FINE_ALIGN_OK
        if _dbg:
            logger.info(f"[TGT_ALIGN] result={'ALIGNED' if aligned else 'MISSED'}")
        return aligned

    def is_sc_assist_gone(self, scr_reg) -> bool:
        """3-of-3 check whether SC Assist has actually disappeared.
        Uses the blue indicator check region only.
        @return: True if SC Assist is confirmed gone (all 3 checks fail).
        """
        gone_count = 0
        for i in range(self.VOTE_COUNT):
            sleep(3)

            # inv_col=False: skip the bogus RGB2BGR conversion in mss capture
            mask = scr_reg.capture_region_filtered(self.scr, 'sc_assist_ind', inv_col=False)

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
        sleep(4)

        # Debug snapshot after boost (closer to station)
        if self.DEBUG_SNAP:
            try:
                snap = self.scrReg.capture_region(self.scr, 'center_normalcruise', inv_col=False)
                if snap is not None:
                    snap_dir = os.path.join('debug-output', 'target-snap')
                    os.makedirs(snap_dir, exist_ok=True)
                    ts = time.strftime('%Y%m%d_%H%M%S')
                    cv2.imwrite(os.path.join(snap_dir, f'approach_{ts}.png'), snap)
                    logger.info(f"Debug snapshot saved: approach_{ts}.png")
            except Exception as e:
                logger.warning(f"Debug snapshot failed: {e}")

        # Pitch up to clear station, then fly clear at full speed
        pitch_time = 75.0 / self.pitchrate
        self.keys.send('PitchUpButton', hold=pitch_time)
        self.set_speed_100()
        sleep(4)

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

    @staticmethod
    def _roll_on_centerline(roll_deg, close):
        """Check if the dot is on the vertical centerline (near 0 or ±180 degrees)."""
        return abs(roll_deg) < close or (180 - abs(roll_deg)) < close

    def _get_dist(self, axis, off):
        """Get distance to target for an axis (ceiled to full degrees)."""
        import math
        if axis == 'roll':
            return math.ceil(min(abs(off['roll']), 180 - abs(off['roll'])))
        return math.ceil(abs(off[axis]))

    def _is_aligned(self, axis, off, close):
        """Check if aligned on an axis."""
        if axis == 'roll':
            return self._roll_on_centerline(off['roll'], close)
        return abs(off[axis]) < close

    def _axis_max_rate(self, axis):
        """Return the known max rate for an axis (from calibration or config)."""
        if axis == 'pit':
            return self.pitchrate
        elif axis == 'yaw':
            return self.yawrate
        return self.rollrate

    def _axis_pick_key(self, axis, deg):
        """Pick the correct key for moving an axis toward center (or toward +-180 for roll).

        <= 90: move toward 0   -> RollRight/PitchUp decreases positive angle
        > 90:  move toward 180 -> INVERT direction (RollLeft/PitchDown increases positive angle)
        """
        if axis == 'roll':
            # Roll toward nearest centerline (0 or 180): same direction regardless
            return 'RollRightButton' if deg > 0 else 'RollLeftButton'
        elif axis == 'pit':
            if abs(deg) <= 90:
                return 'PitchUpButton' if deg > 0 else 'PitchDownButton'
            else:
                return 'PitchDownButton' if deg > 0 else 'PitchUpButton'
        else:
            return 'YawRightButton' if deg > 0 else 'YawLeftButton'

    def _align_axis(self, scr_reg, axis, off, close=10.0, timeout=None):
        """Align one axis using configured rate and calculated holds.
        @return: Updated offset dict, or None if compass lost.
        """
        if timeout is None:
            timeout = self.ALIGN_TIMEOUT
        # Target behind -- don't try to align, let compass_align handle the flip
        if off.get('z', 1) < 0:
            return off

        if self._is_aligned(axis, off, close):
            return off

        start = time.time()
        remaining = self._get_dist(axis, off)
        rate = self._axis_max_rate(axis) * self.ZERO_THROTTLE_RATE_FACTOR
        key = self._axis_pick_key(axis, off[axis])

        logger.info(f"Align {axis}: {off[axis]:.1f}deg, dist={remaining:.1f}, rate={rate:.1f}, key={key}")

        # Correction loop with calculated holds
        while remaining > close and (time.time() - start) < timeout:
            self.check_stop()
            # Progressive approach: gentle near center, bolder far out
            if remaining < 10:
                approach_pct = 0.4
            elif remaining < 20:
                approach_pct = 0.6
            else:
                approach_pct = 0.8

            hold_time = (remaining * approach_pct) / rate
            hold_time = max(self.MIN_HOLD_TIME, min(self.MAX_HOLD_TIME, hold_time))

            logger.debug(f"Align {axis}: remaining={remaining:.1f}deg, hold={hold_time:.2f}s, rate={rate:.1f}, key={key}")
            self.keys.send(key, hold=hold_time)
            sleep(self.ALIGN_SETTLE)

            # FSD jumped during hold/settle -- compass is garbage, bail out
            if self.status.get_flag(FlagsFsdJump):
                logger.info(f"Align {axis}: FSD jumped during align, aborting")
                return off

            new_off = self.get_nav_offset(scr_reg)
            if new_off is None:
                sleep(0.5)
                new_off = self.get_nav_offset(scr_reg)
                if new_off is None:
                    return off

            # Target went behind during alignment -- abort, let compass_align handle the flip
            if new_off.get('z', 1) < 0:
                logger.info(f"Align {axis}: target went behind, aborting axis align")
                return new_off

            if self._is_aligned(axis, new_off, close):
                logger.info(f"Align {axis}: aligned at {new_off[axis]:.1f}deg ({time.time()-start:.1f}s)")
                return new_off

            new_dist = self._get_dist(axis, new_off)

            # Always re-pick key from current position -- prevents runaway when
            # a small overshoot flips the sign
            old_key = key
            key = self._axis_pick_key(axis, new_off[axis])
            if key != old_key:
                logger.debug(f"Align {axis}: direction changed {remaining:.1f}->{new_dist:.1f}, key={key}")

            remaining = new_dist
            off = new_off

        if (time.time() - start) >= timeout:
            logger.warning(f"Align {axis}: timeout after {timeout}s")
        return off

    def _roll_to_centerline(self, scr_reg, off, close=10.0):
        """Coarse roll to vertical centerline (only for large offsets)."""
        return self._align_axis(scr_reg, 'roll', off, close)

    def _yaw_to_center(self, scr_reg, off, close=10.0):
        """Yaw to horizontal center."""
        return self._align_axis(scr_reg, 'yaw', off, close)

    def _pitch_to_center(self, scr_reg, off, close=10.0):
        """Pitch to vertical center."""
        return self._align_axis(scr_reg, 'pit', off, close)

    AVG_DELAY = 0.01  # 10ms between reads

    def _avg_offset(self, scr_reg, get_offset_fn):
        """Take 3 reads with 10ms gaps, return average pit/yaw.
        @param get_offset_fn: callable(scr_reg) -> dict with 'pit','yaw' or None
        @return: dict with avg 'pit','yaw' or None if any read fails.
        """
        reads = []
        for i in range(3):
            if i > 0:
                sleep(self.AVG_DELAY)
            off = get_offset_fn(scr_reg)
            if off is None:
                return None
            reads.append(off)
        return {
            'pit': sum(r['pit'] for r in reads) / 3,
            'yaw': sum(r['yaw'] for r in reads) / 3,
        }

    NUDGE_SAMPLES = 5
    NUDGE_HOLD = 0.4

    NUDGE_BOTH_THRESHOLD = 5.0

    def nudge_align(self, scr_reg) -> bool:
        """Minimal realignment using 5-of-5 navball consensus.
        Nudges both axes if both are above threshold, otherwise worst axis only.
        Returns True if a nudge was applied, False if reads failed."""
        offsets = []
        for _ in range(self.NUDGE_SAMPLES):
            off = self.get_nav_offset(scr_reg)
            if off is None:
                return False
            offsets.append(off)

        avg_pit = sum(o['pit'] for o in offsets) / self.NUDGE_SAMPLES
        avg_yaw = sum(o['yaw'] for o in offsets) / self.NUDGE_SAMPLES
        logger.info(f"nudge_align: avg pit={avg_pit:.1f} yaw={avg_yaw:.1f} (5 samples)")

        if abs(avg_pit) < self.FINE_ALIGN_CLOSE and abs(avg_yaw) < self.FINE_ALIGN_CLOSE:
            logger.info("nudge_align: already aligned, no nudge needed")
            return True

        pit_bad = abs(avg_pit) >= self.FINE_ALIGN_CLOSE
        yaw_bad = abs(avg_yaw) >= self.FINE_ALIGN_CLOSE
        both_bad = abs(avg_pit) >= self.NUDGE_BOTH_THRESHOLD and abs(avg_yaw) >= self.NUDGE_BOTH_THRESHOLD

        if both_bad:
            pit_key = self._axis_pick_key('pit', avg_pit)
            yaw_key = self._axis_pick_key('yaw', avg_yaw)
            logger.info(f"nudge_align: both axes off, {pit_key}+{yaw_key} hold={self.NUDGE_HOLD}s")
            self.keys.send(pit_key, hold=self.NUDGE_HOLD)
            self.keys.send(yaw_key, hold=self.NUDGE_HOLD)
        elif pit_bad and (not yaw_bad or abs(avg_pit) > abs(avg_yaw)):
            key = self._axis_pick_key('pit', avg_pit)
            logger.info(f"nudge_align: {key} hold={self.NUDGE_HOLD}s")
            self.keys.send(key, hold=self.NUDGE_HOLD)
        else:
            key = self._axis_pick_key('yaw', avg_yaw)
            logger.info(f"nudge_align: {key} hold={self.NUDGE_HOLD}s")
            self.keys.send(key, hold=self.NUDGE_HOLD)
        return True

    # Threshold for roll and coarse alignment -- roll to centerline and trigger coarse
    # correction when pit or yaw exceeds this value
    ROLE_YAW_PITCH_CLOSE = 6.0
    # Only roll when yaw is significantly off -- prevents unnecessary rolls near alignment
    ROLE_TRESHHOLD = 8.0
    # Min/max hold time for alignment key presses (SC inertia needs minimum impulse)
    MIN_HOLD_TIME = 0.50
    MAX_HOLD_TIME = 4.0
    # Alignment convergence and timeout
    ALIGN_CLOSE = 4.0           # degrees -- compass jitter is ~3-4 deg
    ALIGN_SETTLE = 2.0          # seconds to let ship/compass settle after pitch/yaw
    ALIGN_TIMEOUT = 25.0        # seconds per axis (allows ~6 cycles with settle)
    # Fine align thresholds
    FINE_ALIGN_CLOSE = 2.0      # degrees -- "already aligned" for target circle
    FINE_ALIGN_OK = 3.0         # degrees -- "close enough" after correction
    # SC Assist detection
    SC_ASSIST_GONE_RATIO = 0.50 # cyan ratio below this = indicator gone
    SC_ASSIST_CHECK_INTERVAL = 3   # seconds between gone checks
    SC_SETTLE_TIME = 5          # seconds to let SC assist settle after engage
    # Target arc detection
    MIN_ARC_PIXELS = 100        # minimum orange pixels to consider as arc
    ARC_STD_THRESHOLD = 12      # radius std below this = arc shape (not text)
    # Evasion pitch angles and cruise time
    OCCLUSION_PITCH = 65
    BODY_EVADE_PITCH = 90
    PASSBODY_TIME = 25
    # Common angles
    HALF_TURN = 180.0           # target behind flip
    QUARTER_TURN = 90           # 90-degree pitch maneuvers
    # Key input settle time for navigation commands
    KEY_WAIT = 0.125
    # Dock approach
    DOCK_PRE_PITCH = 1.0        # seconds pitch up before boost toward station
    # Voting
    VOTE_COUNT = 3              # 3-of-3 consensus checks
    # Turn rate at 0% throttle vs blue zone (50%) -- assumed ~65%
    ZERO_THROTTLE_RATE_FACTOR = 0.60
    # Debug
    DEBUG_SNAP = False           # save debug snapshots to debug-output/
    DEBUG_TARGET_CIRCLE = True   # verbose logging for target circle detection + fine align

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

            # Target behind -- pitch UP to flip (away from star after jump)
            # Max 2x 180° flips, then 1x 90° to break deadlock
            if off['z'] < 0:
                flip_count = getattr(self, '_flip_count', 0)
                effective_rate = self.pitchrate * self.ZERO_THROTTLE_RATE_FACTOR
                if flip_count < 2:
                    flip_deg = 180.0
                elif flip_count == 2:
                    flip_deg = 90.0
                    logger.warning("Compass: 2 flips failed, trying 90deg break")
                else:
                    logger.error("Compass: 3 flips exhausted, giving up")
                    break
                pitch_time = flip_deg / effective_rate
                logger.info(f"Compass: target behind, flip {flip_count+1} pitch {flip_deg:.0f}deg ({pitch_time:.1f}s)")
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
                    pitch_time = 180.0 / effective_rate
                    logger.info(f"Compass: target went behind during roll, flipping up ({pitch_time:.1f}s)")
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
                # Try target circle fine alignment if visible
                if self.is_target_arc_visible(scr_reg):
                    logger.info("Compass close enough, switching to target circle fine align")
                    self.target_fine_align(scr_reg)
                self.ap_ckb('log', 'Compass Align complete')
                return True

            # Single nudge on worst axis, then accept
            self.nudge_align(scr_reg)
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

    def sc_target_align(self, scr_reg) -> ScTargetAlignReturn:
        """ Align to the target, monitoring for disengage and obscured.
        @param scr_reg: The screen region class.
        @return: A string detailing the reason for the method return. Current return options:
            'lost': Lost target
            'found': Target found
            'disengage': Disengage text found
        """
        target_align_compass_mult = 3  # Multiplier to close and target_align_inner_lim when using compass for align.
        target_align_pit_off = 0.25  # In deg. To keep the target above the center line (prevent it going down out of view).

        target_pit = target_align_pit_off
        target_yaw = 0.0

        # Copy locally as we will change the values
        target_align_outer_lim = self.target_align_outer_lim
        target_align_inner_lim = self.target_align_inner_lim

        off = None
        tar_off1 = None
        nav_off1 = None
        tar_off2 = None
        nav_off2 = None
        none_count = 0  # consecutive None reads = likely behind

        # Try to get the target 5 times before quiting
        for i in range(5):
            # Check Target and Compass
            nav_off1 = self.get_nav_offset(scr_reg)
            tar_off1 = self.get_target_offset(scr_reg)
            if tar_off1:
                # Target detected
                off = tar_off1
                none_count = 0
                # Apply offset to keep target above center
                off['pit'] = off['pit'] - target_align_pit_off
            elif nav_off1:
                # Compass found with front dot
                off = nav_off1
                none_count = 0
                self.ap_ckb('log', 'Using Compass for Target Align')

                # We are using compass align, increase the values as compass is much less accurate
                target_align_outer_lim = target_align_outer_lim * target_align_compass_mult
                target_align_inner_lim = target_align_inner_lim * target_align_compass_mult
                target_align_pit_off = target_align_pit_off * target_align_compass_mult
            else:
                # Neither target nor compass dot found -- confirm with 3-of-3 avg
                med = self._avg_offset(scr_reg, self.get_nav_offset)
                if med is not None:
                    # Transient miss, dot is actually there -- retry main loop
                    continue
                # Confirmed no dot -- target is behind, pitch to recover
                self.ap_ckb('log', 'Target behind (confirmed 3/3 avg), pitching to recover')
                for _ in range(6):  # max 6x30=180 degrees
                    self.pitch_up_down(30)
                    dot_hits = sum(1 for _ in range(3) if self.get_nav_offset(scr_reg))
                    if dot_hits >= 2:
                        break
                continue


            # Quit loop if we found Target or Compass
            if off:
                break

        # Target could not be found, return
        if tar_off1 is None and nav_off1 is None:
            logger.debug("sc_target_align not finding target")
            self.ap_ckb('log', 'Target Align failed - target not found')
            return ScTargetAlignReturn.Lost

        # We have Target or Compass. Are we close to Target?
        compass_only_count = 0  # Track iterations with only compass (no target reticle)
        max_compass_only = 3  # Accept "close enough" after this many compass-only iterations
        align_iterations = 0
        max_align_iterations = 15
        close_enough_lim = 3.0  # degrees -- accept if both axes under this
        while (abs(off['pit']) > target_align_outer_lim or
               abs(off.get('yaw', 0)) > target_align_outer_lim):
            self.check_stop()
            align_iterations += 1
            if align_iterations > max_align_iterations:
                self.ap_ckb('log', f'Target Align: max iterations ({max_align_iterations}), accepting')
                break
            # If close enough on both axes, stop chasing sub-degree precision
            if (abs(off['pit']) < close_enough_lim and
                    abs(off.get('yaw', 0)) < close_enough_lim and
                    align_iterations > 3):
                self.ap_ckb('log', f'Target Align: close enough (pit={off["pit"]:+.1f} yaw={off.get("yaw", 0):+.1f})')
                break

            target_align_outer_lim = target_align_inner_lim  # Keep aligning until we are within this lower range.

            # Clear the overlays before moving
            if self.debug_overlay:
                self.overlay.overlay_remove_rect('compass')
                self.overlay.overlay_remove_floating_text('compass')
                self.overlay.overlay_remove_floating_text('nav')
                self.overlay.overlay_remove_floating_text('nav_beh')
                self.overlay.overlay_remove_floating_text('compass_rpy')

                self.overlay.overlay_remove_rect('target')
                self.overlay.overlay_remove_floating_text('target')
                self.overlay.overlay_remove_floating_text('target_occ')
                self.overlay.overlay_remove_floating_text('target_rpy')
                self.overlay.overlay_paint()

            yaw_val = off.get('yaw', 0)
            self.ap_ckb('log', f'Align: pit={off["pit"]:+.1f} yaw={yaw_val:+.1f} roll={off["roll"]:+.1f} lim={target_align_outer_lim:.1f}')

            # When close to center, use yaw directly instead of roll+pitch
            # Roll+pitch oscillates when corrections are small
            if abs(yaw_val) <= 15 and abs(off['pit']) <= 15:
                if abs(yaw_val) > target_align_outer_lim:
                    self.ap_ckb('log', f'Yawing {yaw_val:+.1f}')
                    self.yaw_right_left(yaw_val)
                if abs(off['pit']) > target_align_outer_lim:
                    self.ap_ckb('log', f'Pitching {off["pit"]:+.1f}')
                    self.pitch_up_down(off['pit'])
            else:
                # Far off -- roll to put target on centerline, then pitch
                if abs(yaw_val) > target_align_outer_lim:
                    self.ap_ckb('log', f'Rolling {off["roll"]:+.1f} (yaw={yaw_val:+.1f})')
                    self.roll_clockwise_anticlockwise(off['roll'])
                if abs(off['pit']) > target_align_outer_lim:
                    self.ap_ckb('log', f'Pitching {off["pit"]:+.1f}')
                    self.pitch_up_down(off['pit'])

            # Wait for ship to finish moving and picture to stabilize
            sleep(1.0)

            # Check Target and Compass
            nav_off2 = self.get_nav_offset(scr_reg)
            tar_off2 = self.get_target_offset(scr_reg)
            if tar_off2:
                off = tar_off2
                compass_only_count = 0  # Reset -- we found the target reticle
                self.ap_ckb('log', f'After: TAR pit={off["pit"]:+.1f} roll={off["roll"]:+.1f}')
                # Apply offset to keep target above center
                off['pit'] = off['pit'] - target_align_pit_off
            elif nav_off2:
                # Try to use the compass data if the target is not visible.
                off = nav_off2
                compass_only_count += 1
                self.ap_ckb('log', f'After: NAV pit={off["pit"]:+.1f} roll={off["roll"]:+.1f} ({compass_only_count}/{max_compass_only})')
                # Compass isn't precise enough for tight alignment -- accept "close enough"
                if compass_only_count >= max_compass_only:
                    logger.info(f"sc_target_align: compass-only for {compass_only_count} iterations, accepting current alignment")
                    self.ap_ckb('log', 'Target Align: compass close enough, proceeding')
                    break

            if tar_off1 and tar_off2:
                # Check diff from before and after movement
                pit_delta = tar_off2['pit'] - tar_off1['pit']
                if ((tar_off1['pit'] < 0.0 and tar_off2['pit'] > target_align_outer_lim) or
                        (tar_off1['pit'] > 0.0 and tar_off2['pit'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Pitch correction gone too far. Reducing Pitch Factor.")
                    self.ap_ckb('update_ship_cfg')

            if tar_off2:
                # Store current offsets
                tar_off1 = tar_off2.copy()


            # Check if target is outside the target region (behind us) and break loop
            if tar_off2 is None and nav_off2 is None:
                logger.debug("sc_target_align lost target")
                self.ap_ckb('log', 'Target Align failed - lost target.')
                return ScTargetAlignReturn.Lost

        # We are aligned, so define the navigation correction as the current offset. This won't be 100% accurate, but
        # will be within a few degrees.
        if tar_off1 and nav_off1:
            self._nav_cor_x = max(-5.0, min(5.0, self._nav_cor_x + nav_off1['x']))
            self._nav_cor_y = max(-5.0, min(5.0, self._nav_cor_y + nav_off1['y']))
        elif tar_off2 and nav_off2:
            self._nav_cor_x = max(-5.0, min(5.0, self._nav_cor_x + nav_off2['x']))
            self._nav_cor_y = max(-5.0, min(5.0, self._nav_cor_y + nav_off2['y']))

        # self.ap_ckb('log', 'Target Align complete.')
        return ScTargetAlignReturn.Found

    def occluded_reposition(self, scr_reg):
        """ Reposition is use when the target is occluded by a planet or other.
        We pitch 90 deg down for a bit, then up 90, this should make the target underneath us
        this is important because when we do nav_align() if it does not see the Nav Point
        in the compass (because it is a hollow circle), then it will pitch down, this will
        bring the target into view quickly. """
        self.ap_ckb('log+vce', 'Target occluded, repositioning.')
        self.set_speed_0()
        self.pitch_up_down(-90)

        # Speed away
        self.set_speed_100()
        sleep(15)

        self.set_speed_0()
        self.pitch_up_down(90)
        self.compass_align(scr_reg)
        self.set_speed_50()

    def logout(self):
        """ Performs menu action to log out of game """
        self.update_ap_status("Logout")
        self.keys.send_key('Down', SCANCODE["Key_Escape"])
        sleep(0.5)
        self.keys.send_key('Up', SCANCODE["Key_Escape"])
        sleep(0.5)
        self.keys.send('UI_Up')
        sleep(0.5)
        self.keys.send('UI_Select')
        sleep(0.5)
        self.keys.send('UI_Select')
        sleep(0.5)
        self.update_ap_status("Idle")

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

    # jump() happens after we are aligned to Target
    # TODO: nees to check for Thargoid interdiction and their wave that would shut us down,
    #       if thargoid, then we wait until reboot and continue on.. go back into FSD and align
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
                # FSD still charged? Alignment drifted -- nudge and let FSD pull us in
                if self.status.get_flag(FlagsFsdCharging):
                    logger.info("jump: FSD charged but no jump -- nudging alignment")
                    self.nudge_align(scr_reg)
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

        # Convenience routes to pitch, roll, yaw by specified degrees

    def _move_axis(self, axis, deg):
        """Move on the given axis by deg degrees. Positive = up/right/clockwise."""
        cfg = self._AXIS_CONFIG[axis]
        abs_deg = abs(deg)
        rate = getattr(self, cfg['rate_attr'])
        htime = abs_deg / rate

        if self.speed_demand is None:
            self.set_speed_25()

        # For small angles, use interpolated rate from ship config lookup table
        if abs_deg < cfg['threshold']:
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_cfg = ship_type[self.speed_demand]
            if cfg['lookup_key'] not in speed_cfg:
                speed_cfg[cfg['lookup_key']] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_cfg[cfg['lookup_key']].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    logger.debug(f"{axis} demand: {deg}, lookup: {key_deg}/{value}, ratio: {round(ratio_val, 2)}")
                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        key_name = cfg['pos_key'] if deg > 0.0 else cfg['neg_key']
        self.keys.send(key_name, hold=htime)

    def roll_clockwise_anticlockwise(self, deg):
        self._move_axis('roll', deg)

    def pitch_up_down(self, deg):
        self._move_axis('pitch', deg)

    def yaw_right_left(self, deg):
        self._move_axis('yaw', deg)

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
                    # Starports have mail slots -- wait for LEAVE STATION text to disappear
                    # Require 3 consecutive clear frames to avoid false-clears
                    sleep(15)
                    clear_count = 0
                    for _ in range(30):
                        self.check_stop()
                        snap = self.scrReg.capture_region(self.scr, 'in_station', inv_col=False)
                        if snap is not None:
                            bgr = snap[:, :, :3]
                            lower = np.array([195, 195, 125], dtype=np.uint8)
                            upper = np.array([205, 205, 135], dtype=np.uint8)
                            mask = cv2.inRange(bgr, lower, upper)
                            pct = (np.count_nonzero(mask) / mask.size) * 100
                            if pct < 0.5:
                                clear_count += 1
                                logger.info(f"in_station check: {pct:.1f}% -- clear frame {clear_count}/3")
                                if clear_count >= 3:
                                    break
                            else:
                                clear_count = 0
                                logger.debug(f"in_station check: {pct:.1f}% -- LEAVE STATION still visible")
                        sleep(1)
                    logger.info("Station cleared, waiting 3s before throttle up")
                    sleep(3)
                    self.set_speed_100()
                else:
                    # All non-starport stations: brief wait, then pitch away, boost, clear
                    sleep(5)
                    self.ap_ckb('log+vce', 'Maneuvering away from station')
                    self.set_speed_50()
                    pitch_time = self.config['OCDepartureAngle'] / self.pitchrate
                    self.keys.send('PitchUpButton', hold=pitch_time)
                    self.keys.send('UseBoostJuice')
                    sleep(4)

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
                sleep(5)

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
            sleep(4)
            self.update_ap_status("Undock Complete, accelerating")
            self.sc_engage()

            # Wait until out of orbit.
            res = self.status.wait_for_flag_off(FlagsHasLatLong, timeout=60)
            # TODO - do we need to check if we never leave orbit?

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
            sleep(5)

    def sc_engage(self) -> bool:
        """ Engages supercruise. Clears masslock first (boosting), then SC.
        """
        if self.status.get_flag(FlagsSupercruise):
            return True

        for attempt in range(3):
            self.check_stop()
            self.set_speed_100()
            self.wait_masslock_clear()
            self.keys.send('Supercruise')

            res = self.status.wait_for_flag_on(FlagsSupercruise, timeout=20)
            if res:
                break
            logger.warning(f'sc_engage: not in supercruise after 20s (attempt {attempt+1})')

        return True

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
            self.update_overlay()
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

                # Debug snapshot of what's ahead after SC drop
                if self.DEBUG_SNAP:
                    try:
                        snap = scr_reg.capture_region(self.scr, 'center_normalcruise', inv_col=False)
                        if snap is not None:
                            snap_dir = os.path.join('debug-output', 'target-snap')
                            os.makedirs(snap_dir, exist_ok=True)
                            ts = time.strftime('%Y%m%d_%H%M%S')
                            cv2.imwrite(os.path.join(snap_dir, f'drop_{ts}.png'), snap)
                            logger.info(f"Debug snapshot saved: drop_{ts}.png")
                    except Exception as e:
                        logger.warning(f"Debug snapshot failed: {e}")

                break

            # Body proximity check -- ApproachBody journal event
            approach_body = self.jn.ship_state().get('approach_body')
            if approach_body:
                self.jn.ship['approach_body'] = None  # clear so we don't re-trigger
                sc_assist_cruising = False
                self.ap_ckb('log+vce', f'Approaching body: {approach_body} -- evading')
                logger.info(f"sc_assist: ApproachBody detected: {approach_body}")
                self.keys.send('SetSpeed25')  # deactivate SC Assist
                pitch_time = self.BODY_EVADE_PITCH / self.pitchrate
                self.keys.send('PitchUpButton', hold=pitch_time)
                self.set_speed_100()
                sleep(self.PASSBODY_TIME)
                self.set_speed_0()
                self.compass_align(scr_reg)
                self.keys.send('SetSpeed75')  # re-engage SC Assist
                sleep(self.SC_SETTLE_TIME)
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
                    self.keys.send('SetSpeed25')
                    pitch_time = self.OCCLUSION_PITCH / self.pitchrate
                    self.keys.send('PitchUpButton', hold=pitch_time)
                    self.set_speed_100()
                    sleep(self.PASSBODY_TIME)
                    self.set_speed_0()
                    self.compass_align(scr_reg)
                    self.keys.send('SetSpeed75')
                    sleep(self.SC_SETTLE_TIME)
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
            sleep(2)  # wait for the journal to catch up

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

    def set_cv_view(self, enable=True, x=0, y=0):
        self.cv_view = enable
        self.config['Enable_CV_View'] = int(self.cv_view)  # update the config
        self.update_config()  # save the config
        if enable == True:
            self.cv_view_x = x
            self.cv_view_y = y
        else:
            cv2.destroyAllWindows()
            cv2.waitKey(50)

    def set_randomness(self, enable=False):
        self.config["EnableRandomness"] = enable

    def set_activate_elite_eachkey(self, enable=False):
        self.config["ActivateEliteEachKey"] = enable

    def set_automatic_logout(self, enable=False):
        self.config["AutomaticLogout"] = enable

    def set_overlay(self, enable=False):
        # TODO: apply the change without restarting the program
        self.config["OverlayTextEnable"] = enable
        if not enable:
            self.overlay.overlay_clear()

        self.overlay.overlay_paint()

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
        if self.overlay != None:
            self.overlay.overlay_quit()
        self.terminate = True

    #
    # This function will execute in its own thread and will loop forever until
    # the self.terminate flag is set
    #
    def engine_loop(self):
        while not self.terminate:
            # TODO - Remove these show compass/target all the time
            if self.debug_show_compass_overlay:
                self.get_nav_offset(self.scrReg, True)
            if self.debug_show_target_overlay:
                self.get_target_offset(self.scrReg, True)

            # Ship calibration functions
            if self.ship_tst_roll_enabled:
                self.ship_tst_roll_new(0)
                self.ship_tst_roll_enabled = False
            if self.ship_tst_pitch_enabled:
                self.ship_tst_pitch_new(0)
                self.ship_tst_pitch_enabled = False
            if self.ship_tst_yaw_enabled:
                self.ship_tst_yaw_new(0)
                self.ship_tst_yaw_enabled = False

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
                self._stop_event.clear()
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.update_ap_status("SC to Target")
                    self.sc_assist(self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    logger.exception("SC Assist trapped generic")

                logger.debug("Completed sc_assist")
                if not self.sc_assist_enabled:
                    self.ap_ckb('sc_stop')
                self.update_overlay()

            elif self.waypoint_assist_enabled == True:
                logger.debug("Running waypoint_assist")
                self._stop_event.clear()
                set_focus_elite_window()
                self.update_overlay()
                self.jump_cnt = 0
                self.refuel_cnt = 0
                self.total_dist_jumped = 0
                self.total_jumps = 0
                try:
                    self.waypoint_assist(self.keys, self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    logger.exception("Waypoint Assist trapped generic")

                if not self.waypoint_assist_enabled:
                    self.ap_ckb('waypoint_stop')
                self.update_overlay()

            elif self.dss_assist_enabled == True:
                logger.debug("Running dss_assist")
                self._stop_event.clear()
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.dss_assist()
                except EDAP_Interrupt:
                    logger.debug("Stopping DSS Assist")
                except Exception as e:
                    logger.exception("DSS Assist trapped generic")

                self.dss_assist_enabled = False
                self.ap_ckb('dss_stop')
                self.update_overlay()

            # Check once EDAPGUI loaded to prevent errors logging to the listbox before loaded
            if self.gui_loaded:
                # Check if ship has changed
                ship = self.jn.ship_state()['type']
                # Check if a ship and not a suit (on foot)
                if ship not in ship_size_map:
                    # Clear current ship
                    self.current_ship_type = ''
                else:
                    ship_fullname = EDJournal.get_ship_fullname(ship)

                    # Check if ship changed or just loaded
                    if ship != self.current_ship_type:
                        if self.current_ship_type is not None:
                            cur_ship_fullname = EDJournal.get_ship_fullname(self.current_ship_type)
                            self.ap_ckb('log+vce', f"Switched ship from your {cur_ship_fullname} to your {ship_fullname}.")
                        else:
                            self.ap_ckb('log+vce', f"Welcome aboard your {ship_fullname}.")

                        # Check for fuel scoop and advanced docking computer
                        if not self.jn.ship_state()['has_fuel_scoop']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with a Fuel Scoop.")
                        if not self.jn.ship_state()['has_adv_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with an Advanced Docking Computer.")
                        if self.jn.ship_state()['has_std_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is fitted with a Standard Docking Computer.")

                        # Store ship for change detection BEFORE loading config and GUI update
                        self.current_ship_type = ship

                        # Load ship configuration with proper hierarchy
                        self.load_ship_configuration(ship)

                        # Update GUI with ship config
                        self.ap_ckb('update_ship_cfg')


            self.update_overlay()
            cv2.waitKey(10)
            sleep(1)

    _AXIS_CAL_CONFIG = {
        'pitch': {
            'rate_key': 'PitchRate', 'offset_key': 'pit', 'offset_fn': 'get_target_offset',
            'pos_key': 'PitchUpButton', 'neg_key': 'PitchDownButton',
            'rate_attr': 'pitchrate', 'targ_angles': [5, 10, 20, 40, 80, 160],
            'init_time': 0.05, 'time_mult': 1.04, 'default_angle': 300,
            'overlay_keys': [('rect', 'target'), ('text', 'target'), ('text', 'target_occ'), ('text', 'target_rpy')],
            'move_fn': 'pitch_up_down',
        },
        'roll': {
            'rate_key': 'RollRate', 'offset_key': 'roll', 'offset_fn': 'get_nav_offset',
            'pos_key': 'RollRightButton', 'neg_key': 'RollLeftButton',
            'rate_attr': 'rollrate', 'targ_angles': [40, 80, 160, 320],
            'init_time': 0.05, 'time_mult': 1.03, 'default_angle': 450,
            'overlay_keys': [('rect', 'compass'), ('text', 'compass'), ('text', 'nav'), ('text', 'nav_beh'), ('text', 'compass_rpy')],
            'move_fn': 'roll_clockwise_anticlockwise',
        },
        'yaw': {
            'rate_key': 'YawRate', 'offset_key': 'yaw', 'offset_fn': 'get_target_offset',
            'pos_key': 'YawRightButton', 'neg_key': 'YawLeftButton',
            'rate_attr': 'yawrate', 'targ_angles': [5, 10, 20, 40, 80, 160],
            'init_time': 0.07, 'time_mult': 1.05, 'default_angle': 300,
            'overlay_keys': [('rect', 'target'), ('text', 'target'), ('text', 'target_occ'), ('text', 'target_rpy')],
            'move_fn': 'yaw_right_left',
        },
    }

    def _ship_tst_axis_calibrate(self, axis: str):
        """Generic axis calibration. axis must be 'pitch', 'roll', or 'yaw'."""
        cfg = self._AXIS_CAL_CONFIG[axis]
        name = axis.capitalize()
        self.ap_ckb('log', f"Starting {name} Calibration.")

        if self.speed_demand != 'SCSpeed50':
            self.set_speed_50()

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        ship_type[self.speed_demand][cfg['rate_key']] = dict()

        test_time = cfg['init_time']
        delta_int = 0.0
        offset_fn = getattr(self, cfg['offset_fn'])
        default_rate = getattr(self, cfg['rate_attr'])

        for targ_ang in cfg['targ_angles']:
            while 1:
                set_focus_elite_window()
                off = offset_fn(self.scrReg)
                if not off:
                    logger.debug(f"{name} target lost")
                    break

                if self.debug_overlay:
                    for kind, key in cfg['overlay_keys']:
                        if kind == 'rect':
                            self.overlay.overlay_remove_rect(key)
                        else:
                            self.overlay.overlay_remove_floating_text(key)
                    self.overlay.overlay_paint()

                if off[cfg['offset_key']] > 0:
                    self.keys.send(cfg['pos_key'], hold=test_time)
                else:
                    self.keys.send(cfg['neg_key'], hold=test_time)

                sleep(1)

                off2 = offset_fn(self.scrReg)
                if not off2:
                    logger.debug(f"{name} target lost")
                    break

                delta = abs(off2[cfg['offset_key']] - off[cfg['offset_key']])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * cfg['time_mult']
                rate = round(delta / test_time, 2)
                rate = min(rate, default_rate)
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand][cfg['rate_key']][delta_int] = rate
                    logger.info(f"{name} Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"{name} Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    logger.info(f"Ignored {name} Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        if len(ship_type[self.speed_demand][cfg['rate_key']]) > 0:
            ship_type[self.speed_demand][cfg['rate_key']][cfg['default_angle']] = default_rate
            self.ap_ckb('log', f"Default: {name} Angle: {cfg['default_angle'] // 10}: Rate: {default_rate}")

        self.ap_ckb('log', f"Completed {name} Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def ship_tst_pitch_new(self, angle: float):
        self._ship_tst_axis_calibrate('pitch')

    def ship_tst_roll(self, angle: float):
        set_focus_elite_window()
        sleep(0.25)
        self.roll_clockwise_anticlockwise(angle)

    def ship_tst_roll_new(self, angle: float):
        self._ship_tst_axis_calibrate('roll')

    def ship_tst_yaw(self, angle: float):
        set_focus_elite_window()
        sleep(0.25)
        self.yaw_right_left(angle)

    def ship_tst_yaw_new(self, angle: float):
        self._ship_tst_axis_calibrate('yaw')

    def ship_tst_pitch(self, angle: float):
        set_focus_elite_window()
        sleep(0.25)
        self.pitch_up_down(angle)

    _SPEED_CONFIG = {
        0:   {'demand': 'Speed0',   'sc_demand': 'SCSpeed0',   'key': 'SetSpeedZero'},
        25:  {'demand': 'Speed25',  'sc_demand': 'SCSpeed25',  'key': 'SetSpeed25',  'fallback': 50},
        50:  {'demand': 'Speed50',  'sc_demand': 'SCSpeed50',  'key': 'SetSpeed50'},
        100: {'demand': 'Speed100', 'sc_demand': 'SCSpeed100', 'key': 'SetSpeed100'},
    }

    def _set_speed(self, percent, repeat=1):
        cfg = self._SPEED_CONFIG[percent]
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = cfg['sc_demand']
        else:
            self.speed_demand = cfg['demand']

        try:
            self.keys.send(cfg['key'], repeat)
        except Exception:
            if 'fallback' in cfg:
                logger.warning(f"{cfg['key']} not bound, falling back to {cfg['fallback']}%")
                self._set_speed(cfg['fallback'], repeat)
            else:
                raise

    def set_speed_0(self, repeat=1):
        self._set_speed(0, repeat)

    def set_speed_25(self, repeat=1):
        self._set_speed(25, repeat)

    def set_speed_50(self, repeat=1):
        self._set_speed(50, repeat)

    def set_speed_100(self, repeat=1):
        self._set_speed(100, repeat)

def delete_old_log_files():
    """ Deleted old .log files from the main folder."""
    folder = '.'
    n = 5  # days

    current_time = time.time()
    day = 86400  # seconds in a day

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            if filename.endswith('.log'):
                file_time = os.path.getmtime(file_path)
                if file_time < current_time - day * n:
                    logger.debug(f"Deleting file: '{file_path}'")
                    os.remove(file_path)


def strfdelta(tdelta, fmt='{H:02}h {M:02}m {S:02.0f}s', inputtype='timedelta'):
    """Convert a datetime.timedelta object or a regular number to a custom
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02.0f}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02.0f}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02.0f}'      --> ' 5d  8:04:02'
        '{H}h {S:.0f}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == 'timedelta':
        remainder = tdelta.total_seconds()
    elif inputtype in ['s', 'seconds']:
        remainder = float(tdelta)
    elif inputtype in ['m', 'minutes']:
        remainder = float(tdelta)*60
    elif inputtype in ['h', 'hours']:
        remainder = float(tdelta)*3600
    elif inputtype in ['d', 'days']:
        remainder = float(tdelta)*86400
    elif inputtype in ['w', 'weeks']:
        remainder = float(tdelta)*604800
    else:
        remainder = 0.0

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('Y','m','W', 'D', 'H', 'M', 'S', 'mS', 'µS')
    constants = {'Y':86400*365.24,'m': 86400*30.44 ,'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1, 'mS': 1/pow(10,3) , 'µS':1/pow(10,6)}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            quotient, remainder = divmod(remainder, constants[field])
            values[field] = int(quotient) if field != 'S' else quotient + remainder
    return f.format(fmt, **values)


def get_timestamped_filename(prefix: str, suffix: str, extension: str):
    """ Get timestamped filename with milliseconds.
    @return: String in the format of 'prefix yyyy-mm-dd hh-mm-ss.xxx suffix.extension'
    """
    now = datetime.now()
    x = now.strftime("%Y-%m-%d %H-%M-%S.%f")[:-3]  # Date time with mS.
    if prefix != '':
        x = prefix + ' ' + x
    if suffix != '':
        x = x + ' ' + suffix
    x = x + "." + extension
    return x


def dummy_cb(msg, body=None):
    pass


#
# This main is for testing purposes.
#
def main():
    #handle = win32gui.FindWindow(0, "Elite - Dangerous (CLIENT)")
    #if handle != None:
    #    win32gui.SetForegroundWindow(handle)  # put the window in foreground

    delete_old_log_files()

    ed_ap = EDAutopilot(cb=dummy_cb, doThread=False)

    # for x in range(10):
    #     ed_ap.keys.send('RollLeftButton', 0.04)
    # sleep(1)

    set_focus_elite_window()
    ed_ap.set_speed_50()
    sleep(0.25)

    tar_off = ed_ap.get_target_offset(ed_ap.scrReg)
    if tar_off:
        off = tar_off
        logger.debug(f"sc_target_align before: pit:{off['pit']} yaw: {off['yaw']} ")

    # ed_ap.rotateLeft(1)
    x = 10
    ed_ap.pitch_up_down(-x)

    sleep(.5)

    tar_off = ed_ap.get_target_offset(ed_ap.scrReg)
    if tar_off:
        off = tar_off
        logger.debug(f"sc_target_align after: pit:{off['pit']} roll: {off['roll']} ")

    sleep(.5)

    ed_ap.pitch_up_down(x)

    # ed_ap.yawLeft(1)

    # for x in range(10):
    #     ed_ap.keys.send('PitchUpButton', 0.04)
    # sleep(1)
    # for x in range(10):
    #     ed_ap.keys.send('YawLeftButton', 0.04)

        #target_align(scrReg)
        # print("Calling nav_align")
        #ed_ap.nav_align(ed_ap.scrReg)

        #loc = get_destination_offset(scrReg)
        #print("get_dest: " +str(loc))
        #loc = get_nav_offset(scrReg)
        #print("get_nav: " +str(loc))
        # cv2.waitKey(0)
        # print("Done nav")
        # sleep(8)

    # ed_ap.overlay.overlay_quit()




if __name__ == "__main__":
    main()
