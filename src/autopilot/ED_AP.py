import ctypes
import math
import os
import threading
import time
import traceback
from copy import copy
from datetime import datetime, timedelta
from time import sleep
from enum import Enum
from math import atan, degrees
import random
from string import Formatter
from tkinter import messagebox

import cv2
import numpy as np
import kthread
from ultralytics import YOLO

from src.gui.EDAPColonizeEditor import read_json_file, write_json_file
from src.screen.MachineLearning import MachLearn
from simple_localization import LocalizationManager

from src.autopilot.EDAP_EDMesg_Server import EDMesgServer
from src.core.EDAP_data import (
    FlagsDocked, FlagsLanded, FlagsLandingGearDown, FlagsSupercruise, FlagsFsdMassLocked,
    FlagsFsdCharging, FlagsFsdCooldown, FlagsFsdJump, FlagsLowFuel,
    FlagsOverHeating, FlagsHasLatLong, FlagsBeingInterdicted,
    FlagsAnalysisMode, Flags2FsdHyperdriveCharging, Flags2FsdScoActive,
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

    def __init__(self, cb, doThread=True):
        self.config = {}
        self.ship_configs = {
            "Ship_Configs": {},  # Dictionary of ship types with additional settings
        }
        self._sc_sco_active_loop_thread = None
        self._sc_sco_active_loop_enable = False
        self.sc_sco_is_active = 0
        self._sc_sco_active_on_ls = 0
        self._prev_star_system = None
        self.honk_thread = None
        self.speed_demand = None
        self._ocr = None
        self._mach_learn = None
        self._sc_disengage_active = False  # Is SC Disengage active
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
    def mach_learn(self) -> MachLearn:
        """ Load Machine Learning class when needed. """
        if not self._mach_learn:
            self._mach_learn = MachLearn(self, self.ap_ckb)
        return self._mach_learn

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
        # NOTE!!! When adding a new config value below, add the same after read_config() to set
        # a default value or an error will occur reading the new value!
        self.config = {
            "DSSButton": "Primary",  # if anything other than "Primary", it will use the Secondary Fire button for DSS
            "JumpTries": 3,  #
            "NavAlignTries": 3,  #
            "RefuelThreshold": 65,  # if fuel level get below this level, it will attempt refuel
            "FuelThreasholdAbortAP": 10, # level at which AP will terminate, because we are not scooping well
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
            "FCDepartureTime": 5.0,  # Extra time to fly away from a Fleet Carrier
            "FCDepartureAngle": 90.0,  # Angle to pitch up when leaving a Fleet Carrier
            "OCDepartureAngle": 90.0,  # Angle to pitch up when leaving an Orbital Construction Site
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
        # NOTE!!! When adding a new config value above, add the same after read_config() to set
        # a default value or an error will occur reading the new value!

        cnf = read_json_file(filepath='./configs/AP.json')
        # if we read it then point to it, otherwise use the default table above
        if cnf is not None:
            # NOTE!!! Add default values for new entries below!
            if 'SunBrightThreshold' not in cnf:
                cnf['SunBrightThreshold'] = 125
            if 'TargetScale' not in cnf:
                cnf['TargetScale'] = 1.0
            if 'ScreenScale' not in cnf:
                cnf['ScreenScale'] = 1.0
            if 'AutomaticLogout' not in cnf:
                cnf['AutomaticLogout'] = False
            if 'FCDepartureTime' not in cnf:
                cnf['FCDepartureTime'] = 5.0
            if 'Language' not in cnf:
                cnf['Language'] = 'en'
            if 'OCRLanguage' not in cnf:
                cnf['OCRLanguage'] = 'en'
            if 'EnableEDMesg' not in cnf:
                cnf['EnableEDMesg'] = False
            if 'EDMesgActionsPort' not in cnf:
                cnf['EDMesgActionsPort'] = 15570
            if 'EDMesgEventsPort' not in cnf:
                cnf['EDMesgEventsPort'] = 15571
            if 'DebugOverlay' not in cnf:
                cnf['DebugOverlay'] = False
            if 'HotkeysEnable' not in cnf:
                cnf['HotkeysEnable'] = False
            if 'WaypointFilepath' not in cnf:
                cnf['WaypointFilepath'] = ""
            if 'DebugOCR' not in cnf:
                cnf['DebugOCR'] = False
            if 'DebugImages' not in cnf:
                cnf['DebugImages'] = False
            if 'Key_ModDelay' not in cnf:
                cnf['Key_ModDelay'] = 0.01
            if 'Key_DefHoldTime' not in cnf:
                cnf['Key_DefHoldTime'] = 0.2
            if 'Key_RepeatDelay' not in cnf:
                cnf['Key_RepeatDelay'] = 0.1
            if 'DisengageUseMatch' not in cnf:
                cnf['DisengageUseMatch'] = False
            if 'target_align_outer_lim' not in cnf:
                cnf['target_align_outer_lim'] = 1.0  # For test
            if 'target_align_inner_lim' not in cnf:
                cnf['target_align_inner_lim'] = 0.5  # For test
            if 'Debug_ShowCompassOverlay' not in cnf:
                cnf['Debug_ShowCompassOverlay'] = False  # For test
            if 'Debug_ShowTargetOverlay' not in cnf:
                cnf['Debug_ShowTargetOverlay'] = False  # For test
            if 'GalMap_SystemSelectDelay' not in cnf:
                cnf['GalMap_SystemSelectDelay'] = 0.5
            if 'FCDepartureAngle' not in cnf:
                cnf['FCDepartureAngle'] = 90.0
            if 'OCDepartureAngle' not in cnf:
                cnf['OCDepartureAngle'] = 90.0
            if 'PlanetDepartureSCOTime' not in cnf:
                cnf['PlanetDepartureSCOTime'] = 5.0
            if 'FleetCarrierMonitorCAPIDataPath' not in cnf:
                cnf['FleetCarrierMonitorCAPIDataPath'] = ""
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

        # if ship_type in ship_rpy_factor_sc_50:
        #     ship_defaults = ship_rpy_factor_sc_50[ship_type]
        #     # Use default configuration - this means it's been modified and saved to ship_configs.json
        #     self.rollfactor = ship_defaults.get('RollFactor', 20.0)
        #     self.pitchfactor = ship_defaults.get('PitchFactor', 12.0)
        #     self.yawfactor = ship_defaults.get('YawFactor', 12.0)
        #     # return

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
            self.set_speed_0()
            sleep(0.5)

        # In normal space now -- boost away and escape
        self.set_speed_100()

        # Wait for FSD cooldown to start
        self.status.wait_for_flag_on(FlagsFsdCooldown)

        # Boost while waiting for cooldown to complete
        while not self.status.wait_for_flag_off(FlagsFsdCooldown, timeout=1):
            self.keys.send('UseBoostJuice')

        # Back to supercruise
        self.sc_engage(True)

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

        full_compass_image = scr_reg.capture_region(self.scr, 'compass', inv_col=False)

        _t1 = _time.perf_counter()

        # ML test
        maxVal = 0
        compass_quad = Quad()
        full_compass_image2 = cv2.cvtColor(full_compass_image, cv2.COLOR_BGRA2BGR)
        ml_res = self.mach_learn.predict(full_compass_image2)

        _t2 = _time.perf_counter()

        if ml_res and len(ml_res) == 1:
            maxVal = ml_res[0].match_pct
            compass_quad = ml_res[0].bounding_quad
            logger.debug(f"YOLO compass: conf={maxVal:.3f} box=({compass_quad.get_left():.0f},{compass_quad.get_top():.0f},{compass_quad.get_right():.0f},{compass_quad.get_bottom():.0f}) capture={_t1-_t0:.3f}s yolo={_t2-_t1:.3f}s")
        else:
            # Log screenshot for diagnostics/training
            logger.debug(f"YOLO compass: NO MATCH capture={_t1-_t0:.3f}s yolo={_t2-_t1:.3f}s")
            if self.debug_images:
                f = get_timestamped_filename('[get_nav_offset] no_compass_match', '', 'png')
                cv2.imwrite(f'{self.debug_image_folder}/{f}', full_compass_image2)
            return None

        pt = [compass_quad.get_left(), compass_quad.get_top()]

        c_left = scr_reg.reg['compass']['rect'][0]
        c_top = scr_reg.reg['compass']['rect'][1]
        compass_region = Quad.from_rect(scr_reg.reg['compass']['rect'])

        # cut out the compass from the region
        compass_image = Screen.crop_image_pix(full_compass_image, compass_quad)
        comp_h, comp_w = compass_image.shape[:2]

        # Find nav dot by color instead of template matching
        # Convert to HSV for color-based detection
        if compass_image.shape[2] == 4:
            compass_bgr = cv2.cvtColor(compass_image, cv2.COLOR_BGRA2BGR)
        else:
            compass_bgr = compass_image
        compass_hsv = cv2.cvtColor(compass_bgr, cv2.COLOR_BGR2HSV)

        # Mask out the orange compass ring (hue ~5-25, high saturation)
        orange_mask = cv2.inRange(compass_hsv, (5, 100, 100), (25, 255, 255))

        # Look for cyan dot (front target): hue ~75-105, val 170+
        # Front dot is cyan (hue~90, sat~80, val~204)
        front_mask = cv2.inRange(compass_hsv, (75, 40, 170), (105, 255, 255))
        front_mask = cv2.bitwise_and(front_mask, cv2.bitwise_not(orange_mask))

        # Try front dot by color
        final_z_pct = 0.0
        dot_cx, dot_cy = comp_w / 2, comp_h / 2  # default to center

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

        if final_z_pct == 0.0:
            # No cyan front dot = target is behind. YOLO found the compass, so it's not a detection failure.
            _t3 = _time.perf_counter()
            logger.debug(f"Dot: BEHIND comp={comp_w}x{comp_h} contours={len(contours)} areas={all_areas[:5]} total={_t3-_t0:.3f}s")
            return {'x': 0, 'y': 0, 'z': -1, 'roll': 180.0, 'pit': 180.0, 'yaw': 0}

        # Convert dot position to percentage (-1.0 to 1.0)
        compass_x_max = comp_w
        compass_y_max = comp_h

        # Continue calc -- dot_cx/dot_cy is the centroid of the nav dot
        final_x_pct = 2 * (dot_cx / compass_x_max) - 1.0  # X as percent (-1.0 to 1.0, 0.0 in the center)
        final_x_pct = final_x_pct - self._nav_cor_x
        final_x_pct = max(min(final_x_pct, 1.0), -1.0)

        final_y_pct = -(2 * (dot_cy / compass_y_max) - 1.0)  # Y as percent (-1.0 to 1.0, 0.0 in the center), flip Y
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

        # 'longitudinal' radius of compass at given 'latitude'
        lng_rad_at_lat = math.cos(math.asin(final_y_pct))
        lng_rad_at_lat = max(lng_rad_at_lat, 0.001)  # Prevent div by zero

        # 'Latitudinal' radius of compass at given 'longitude'
        lat_rad_at_lng = math.sin(math.acos(final_x_pct))
        lat_rad_at_lng = max(lat_rad_at_lng, 0.001)  # Prevent div by zero

        # Pitch and yaw as a % of the max as defined by the compass circle
        pit_pct = max(min(final_y_pct/lat_rad_at_lng, 1.0), -1.0)
        yaw_pct = max(min(final_x_pct/lng_rad_at_lat, 1.0), -1.0)

        if final_z_pct > 0:
            # Front hemisphere: 0 = dead ahead, +90 = top edge, -90 = bottom edge
            final_pit_deg = (-1 * degrees(math.acos(pit_pct))) + 90
            final_yaw_deg = (-1 * degrees(math.acos(yaw_pct))) + 90
        else:
            # Behind hemisphere: +90..+180 = behind above, -90..-180 = behind below
            # +/-180 = dead behind center
            if final_y_pct > 0:
                final_pit_deg = degrees(math.acos(pit_pct)) + 90   # +90 to +180
            else:
                final_pit_deg = degrees(math.acos(pit_pct)) - 270  # -90 to -180

            if final_x_pct > 0:
                final_yaw_deg = degrees(math.acos(yaw_pct)) + 90   # +90 to +180
            else:
                final_yaw_deg = degrees(math.acos(yaw_pct)) - 270  # -90 to -180

        result = {'x': round(final_x_pct, 4), 'y': round(final_y_pct, 4), 'z': round(final_z_pct, 2),
                  'roll': round(final_roll_deg, 2), 'pit': round(final_pit_deg, 2), 'yaw': round(final_yaw_deg, 2)}

        # Draw box around region
        if self.debug_overlay:
            border = 10  # border to prevent the box from interfering with future matches
            left = c_left + compass_quad.get_left()
            top = c_top + compass_quad.get_top()
            # Copy compass quad and offset to screen co-ords
            compass_to_screen = copy(compass_quad)
            compass_to_screen.offset(compass_region.get_left(), compass_region.get_top())
            compass_with_border = copy(compass_to_screen)
            compass_with_border.inflate(10, 10)

            self.overlay.overlay_rect('compass', (compass_with_border.get_left(), compass_with_border.get_top()), (compass_with_border.get_right(), compass_with_border.get_bottom()), (0, 255, 0), 2)
            self.overlay.overlay_floating_text('compass', f'YOLO: {maxVal:5.2f}', left - border, top - border - 45, (0, 255, 0))
            self.overlay.overlay_floating_text('compass_rpy', f'r: {round(final_roll_deg, 2)} p: {round(final_pit_deg, 2)} y: {round(final_yaw_deg, 2)}', left - border, top + compass_quad.get_height() + border, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            icompass_image_d = full_compass_image
            self.draw_match_rect(icompass_image_d, pt, (pt[0]+compass_quad.get_width(), pt[1]+compass_quad.get_height()), (0, 0, 255), 2)
            icompass_image_d = cv2.rectangle(icompass_image_d, (0, 0), (1000, 45), (0, 0, 0), -1)
            cv2.putText(icompass_image_d, f'YOLO: {maxVal:5.4f}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'x: {final_x_pct:5.2f} y: {final_y_pct:5.2f} z: {final_z_pct:5.2f}', (1, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'r: {final_roll_deg:5.2f}deg p: {final_pit_deg:5.2f}deg y: {final_yaw_deg:5.2f}deg', (1, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('compass', icompass_image_d)
            cv2.moveWindow('compass', self.cv_view_x - 400, self.cv_view_y + 600)
            cv2.waitKey(30)

        return result

    def is_target_occluded(self, scr_reg) -> bool:
        """Detect occlusion warning text in center of screen.
        Only call during SC Assist AFTER speed is set (throttle text gone).
        @return: True if orange warning text detected in center band.
        """
        filtered = scr_reg.capture_region_filtered(self.scr, 'center_text')
        if filtered is None:
            return False
        pixel_count = cv2.countNonZero(filtered)
        total_pixels = filtered.shape[0] * filtered.shape[1]
        ratio = pixel_count / total_pixels if total_pixels > 0 else 0
        if ratio > 0.005:
            logger.info(f"is_target_occluded: orange text detected (ratio={ratio:.4f})")
            return True
        return False

    def _find_target_circle(self, image_bgr):
        """Find the orange target circle in an image using color detection.
        @return: (center_x, center_y) or None if no orange circle found.
        """
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

        # Orange filter for normal target circle
        orange_mask = cv2.inRange(hsv, np.array([16, 165, 220]), np.array([98, 255, 255]))

        # Min area for a valid target arc (scales with image size)
        min_arc_area = max(30, image_bgr.shape[0] * image_bgr.shape[1] * 0.0001)

        best_contour = None

        contours, _ = cv2.findContours(orange_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            for c in sorted(contours, key=cv2.contourArea, reverse=True):
                area = cv2.contourArea(c)
                if area < min_arc_area:
                    break

                x, y, cw, ch = cv2.boundingRect(c)
                rect_area = cw * ch
                if rect_area == 0:
                    continue

                fill_ratio = area / rect_area
                aspect = max(cw, ch) / max(min(cw, ch), 1)

                if fill_ratio < 0.5 and aspect < 3.0 and min(cw, ch) > 15:
                    best_contour = c
                    break

        if best_contour is None:
            return None

        (cx, cy), radius = cv2.minEnclosingCircle(best_contour)
        logger.debug(f"_find_target_circle: center=({cx:.0f},{cy:.0f}) radius={radius:.0f}")
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

    def sc_disengage_label_up(self, scr_reg) -> bool:
        """ Check if SC disengage happened by checking journal status.
        SC Assist auto-drops from supercruise, so we detect via status change
        instead of screen template matching. """
        # Check if we left supercruise (SC Assist dropped us)
        if not self.status.get_flag(FlagsSupercruise):
            return True
        # Also check journal for destination drop event
        if self.jn.ship_state()['status'] == 'in_space':
            return True
        return False

    def start_sco_monitoring(self):
        """ Start Supercruise Overcharge Monitoring. This starts a parallel thread used to detect SCO
        until stop_sco_monitoring if called. """
        self._sc_sco_active_loop_enable = True

        if self._sc_sco_active_loop_thread is None or not self._sc_sco_active_loop_thread.is_alive():
            self._sc_sco_active_loop_thread = threading.Thread(target=self._sc_sco_active_loop, daemon=True)
            self._sc_sco_active_loop_thread.start()

    def stop_sco_monitoring(self):
        """ Stop Supercruise Overcharge Monitoring. """
        self._sc_sco_active_loop_enable = False
        self._sc_disengage_active = False

    def _sc_sco_active_loop(self):
        """ A loop to determine is Supercruise Overcharge is active.
        This runs on a separate thread monitoring the status in the background. """
        while self._sc_sco_active_loop_enable:
            # deactivate if not in SC
            if not self.status.get_flag(FlagsSupercruise):
                self.stop_sco_monitoring()
                break

            start_time = time.time()

            # Try to determine if the disengage/sco text is there
            sc_sco_is_active_ls = self.sc_sco_is_active

            # Check if SCO active in flags
            self.sc_sco_is_active = self.status.get_flag2(Flags2FsdScoActive)

            if self.sc_sco_is_active and not sc_sco_is_active_ls:
                self.ap_ckb('log+vce', "Supercruise Overcharge activated")
            if sc_sco_is_active_ls and not self.sc_sco_is_active:
                self.ap_ckb('log+vce', "Supercruise Overcharge deactivated")

            # Protection if SCO is active
            if self.sc_sco_is_active:
                if self.status.get_flag(FlagsOverHeating):
                    logger.info("SCO Aborting, overheating")
                    self.ap_ckb('log+vce', "SCO Aborting, overheating")
                    self.keys.send('UseBoostJuice')
                elif self.status.get_flag(FlagsLowFuel):
                    logger.info("SCO Aborting, < 25% fuel")
                    self.ap_ckb('log+vce', "SCO Aborting, < 25% fuel")
                    self.keys.send('UseBoostJuice')
                elif self.jn.ship_state()['fuel_percent'] < self.config['FuelThreasholdAbortAP']:
                    logger.info("SCO Aborting, < users low fuel threshold")
                    self.ap_ckb('log+vce', "SCO Aborting, < users low fuel threshold")
                    self.keys.send('UseBoostJuice')

            # Check SC Disengage via journal/status (no screen detection needed)
            if not self.sc_sco_is_active:
                self._sc_disengage_active = self.sc_disengage_label_up(self.scrReg)
            else:
                self._sc_disengage_active = False

            # Status checks are fast, poll every 0.5s
            elapsed_time = time.time() - start_time
            if elapsed_time < 0.5:
                sleep(0.5 - elapsed_time)

    def undock(self):
        """ Performs menu action to undock from Station """
        MenuNav.undock(self.keys, self.status)
        self.set_speed_0(repeat=2)

        # Performs left menu ops to request docking

    def request_docking(self):
        """ Request docking from Nav Panel. """
        self.nav_panel.request_docking()

    def dock(self):
        """ Docking sequence.  Assumes in normal space, will get closer to the Station
        then zero the velocity and execute menu commands to request docking, when granted
        will wait a configurable time for dock.  Perform Refueling and Repair.
        """
        # if not in normal space, give a few more sections as at times it will take a little bit
        if self.jn.ship_state()['status'] != "in_space":
            sleep(3)  # sleep a little longer

        if self.jn.ship_state()['status'] != "in_space":
            logger.error('In dock(), after wait, but still not in_space')

        if self.jn.ship_state()['status'] != "in_space":
            self.set_speed_0()
            logger.error('In dock(), after long wait, but still not in_space')
            raise Exception('Docking failed (not in space)')

        # Slight pitch up to avoid collisions, then boost into docking range
        self.keys.send('PitchUpButton', hold=1.0)
        sleep(0.5)
        self.keys.send('UseBoostJuice')
        sleep(8)
        self.set_speed_0(repeat=2)
        sleep(3)  # Wait for ship to come to stop
        self.ap_ckb('log+vce', "Initiating Docking Procedure")
        # Request docking through Nav panel.
        self.request_docking()
        sleep(1)

        tries = self.config['DockingRetries']
        granted = False
        if self.jn.ship_state()['status'] == "dockinggranted":
            granted = True
        else:
            for i in range(tries):
                if self.jn.ship_state()['no_dock_reason'] == "Distance":
                    self.set_speed_50()
                    sleep(5)
                    self.set_speed_0(repeat=2)
                sleep(3)  # Wait for ship to come to stop
                # Request docking through Nav panel.
                self.request_docking()
                self.set_speed_0(repeat=2)

                sleep(1.5)
                if self.jn.ship_state()['status'] == "dockinggranted":
                    granted = True
                    # Go back to navigation tab
                    #self.request_docking_cleanup()
                    break
                if self.jn.ship_state()['status'] == "dockingdenied":
                    pass

        if not granted:
            self.ap_ckb('log', 'Docking denied: '+str(self.jn.ship_state()['no_dock_reason']))
            logger.warning('Did not get docking authorization, reason:'+str(self.jn.ship_state()['no_dock_reason']))
            raise Exception('Docking failed (Did not get docking authorization)')
        else:
            self.ap_ckb('log+vce', "Docking request granted")
            # allow auto dock to take over
            for i in range(self.config['WaitForAutoDockTimer']):
                sleep(1)
                if self.jn.ship_state()['status'] == "in_station":
                    MenuNav.refuel_repair_rearm(self.keys, self.status)
                    return

            self.ap_ckb('log', 'Auto dock timer timed out.')
            logger.warning('Auto dock timer timed out. Aborting Docking.')
            raise Exception('Docking failed (Auto dock timer timed out)')

    def is_sun_dead_ahead(self, scr_reg):
        return scr_reg.sun_percent(scr_reg.screen) > 5

    # use to orient the ship to not be pointing right at the Sun
    # Checks brightness in the region in front of us, if brightness exceeds a threshold
    # then will pitch up until below threshold.
    #
    def sun_avoid(self, scr_reg):
        logger.debug('align= avoid sun')

        sleep(0.5)

        # close to core the 'sky' is very bright with close stars, if we are pitch due to a non-scoopable star
        #  which is dull red, the star field is 'brighter' than the sun, so our sun avoidance could pitch up
        #  endlessly. So we will have a fail_safe_timeout to kick us out of pitch up if we've pitch past 110 degrees, but
        #  we'll add 3 more second for pad in case the user has a higher pitch rate than the vehicle can do
        fail_safe_timeout = (120/self.pitchrate)+3
        starttime = time.time()

        # if sun in front of us, then keep pitching up until it is below us
        while self.is_sun_dead_ahead(scr_reg):
            self.keys.send('PitchUpButton', state=1)

            # check if we are being interdicted
            interdicted = self.interdiction_check()
            if interdicted:
                # Continue journey after interdiction
                self.set_speed_0()

            # if we are pitching more than N seconds break, may be in high density area star area (close to core)
            if ((time.time()-starttime) > fail_safe_timeout):
                logger.debug('sun avoid failsafe timeout')
                print("sun avoid failsafe timeout")
                break

        self.keys.send('PitchUpButton', state=0)  # release pitch key
        self.set_speed_50()

    @staticmethod
    def _roll_on_centerline(roll_deg, close):
        """Check if the dot is on the vertical centerline (near 0 or ±180 degrees)."""
        return abs(roll_deg) < close or (180 - abs(roll_deg)) < close

    def _get_dist(self, axis, off):
        """Get distance to target for an axis."""
        if axis == 'roll':
            return min(abs(off['roll']), 180 - abs(off['roll']))
        return abs(off[axis])

    def _is_aligned(self, axis, off, close):
        """Check if aligned on an axis."""
        if axis == 'roll':
            return self._roll_on_centerline(off['roll'], close)
        return abs(off[axis]) < close

    def _align_axis(self, scr_reg, axis, off, close=10.0, timeout=20.0):
        """Align one axis using calibration pulse to measure rate, then calculated holds.
        Reverses direction if moving wrong way. Works for roll, pitch, or yaw.
        @return: Updated offset dict, or None if compass lost.
        """
        if self._is_aligned(axis, off, close):
            return off

        start = time.time()
        deg = off[axis]
        dist = self._get_dist(axis, off)

        # Determine key direction (shortest path to target)
        if axis == 'roll':
            if abs(deg) <= 90:
                key = 'RollRightButton' if deg > 0 else 'RollLeftButton'
            else:
                key = 'RollLeftButton' if deg > 0 else 'RollRightButton'
        elif axis == 'pit':
            # Same logic as roll: if behind (>90), flip direction for shortest path
            if abs(deg) <= 90:
                key = 'PitchUpButton' if deg > 0 else 'PitchDownButton'
            else:
                key = 'PitchDownButton' if deg > 0 else 'PitchUpButton'
        else:
            key = 'YawRightButton' if deg > 0 else 'YawLeftButton'

        logger.info(f"Align {axis}: {deg:.1f}deg, dist={dist:.1f}, key={key}")

        # Calibration pulse to measure rate
        cal_time = random.uniform(1.0, 1.5)
        self.keys.send(key, hold=cal_time)
        sleep(0.3)

        new_off = self.get_nav_offset(scr_reg)
        if new_off is None:
            sleep(0.5)
            new_off = self.get_nav_offset(scr_reg)
            if new_off is None:
                return off

        if self._is_aligned(axis, new_off, close):
            logger.info(f"Align {axis}: aligned after cal pulse at {new_off[axis]:.1f}deg")
            return new_off

        new_dist = self._get_dist(axis, new_off)
        moved = dist - new_dist

        if moved <= 0:
            # Wrong direction -- flip key, use measured rate
            key_map = {
                'RollLeftButton': 'RollRightButton', 'RollRightButton': 'RollLeftButton',
                'PitchUpButton': 'PitchDownButton', 'PitchDownButton': 'PitchUpButton',
                'YawLeftButton': 'YawRightButton', 'YawRightButton': 'YawLeftButton',
            }
            key = key_map[key]
            rate = max(abs(moved) / cal_time, 1.0)  # floor at 1 deg/s to avoid div-by-zero
            logger.info(f"Align {axis}: wrong way, reversed to {key}, rate={rate:.1f}deg/s")
        else:
            rate = max(moved / cal_time, 1.0)  # floor at 1 deg/s to avoid div-by-zero
            logger.info(f"Align {axis}: rate={rate:.1f}deg/s (moved {moved:.1f}deg in {cal_time:.1f}s)")

        remaining = new_dist
        off = new_off

        # Correction loop with calculated holds
        max_hold = 2.0  # cap hold time to prevent massive overshoots
        while remaining > close and (time.time() - start) < timeout:
            # More conservative as we get closer, but not too timid
            approach_pct = 0.7 if remaining < 10 else 0.85
            hold_time = (remaining * approach_pct) / rate
            hold_time = max(0.10, min(max_hold, hold_time))

            logger.info(f"Align {axis}: remaining={remaining:.1f}deg, hold={hold_time:.2f}s, rate={rate:.1f}")
            self.keys.send(key, hold=hold_time)
            sleep(0.3)

            new_off = self.get_nav_offset(scr_reg)
            if new_off is None:
                sleep(0.5)
                new_off = self.get_nav_offset(scr_reg)
                if new_off is None:
                    return off

            if self._is_aligned(axis, new_off, close):
                logger.info(f"Align {axis}: aligned at {new_off[axis]:.1f}deg ({time.time()-start:.1f}s)")
                return new_off

            new_dist = self._get_dist(axis, new_off)
            if new_dist > remaining + 5:
                # Overshot -- recalculate direction from new position
                logger.info(f"Align {axis}: overshot {remaining:.1f}->{new_dist:.1f}, recalculating")
                deg = new_off[axis]
                if axis == 'roll':
                    if abs(deg) <= 90:
                        key = 'RollRightButton' if deg > 0 else 'RollLeftButton'
                    else:
                        key = 'RollLeftButton' if deg > 0 else 'RollRightButton'
                elif axis == 'pit':
                    if abs(deg) <= 90:
                        key = 'PitchUpButton' if deg > 0 else 'PitchDownButton'
                    else:
                        key = 'PitchDownButton' if deg > 0 else 'PitchUpButton'
                else:
                    key = 'YawRightButton' if deg > 0 else 'YawLeftButton'
                # Halve rate and reduce max hold after each overshoot
                rate = rate * 0.5
                max_hold = max(0.5, max_hold * 0.6)
            else:
                # Update rate from actual movement (only when NOT overshooting)
                actual_moved = remaining - new_dist
                if actual_moved > 0 and hold_time > 0.15:
                    rate = actual_moved / hold_time

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

    # Roll threshold: only roll when dot is more than this far off the vertical centerline
    COARSE_ROLL_THRESHOLD = 45.0

    def _cal_recover(self, scr_reg, undo_key, pulse_time):
        """After losing compass during calibration, reverse double the pulse to recover.
        @return: offset dict or None if still lost.
        """
        recover_time = pulse_time * 2.0
        logger.info(f"calibrate_rates: recovering with {undo_key} hold={recover_time:.2f}s")
        self.keys.send(undo_key, hold=recover_time)
        sleep(0.3)
        off = self.get_nav_offset(scr_reg)
        return off if off and off['z'] >= 0 else None

    def calibrate_rates(self, scr_reg) -> bool:
        """Measure actual pitch/yaw/roll rates in SC by pulsing each axis for 1s.
        Call once after entering supercruise at 50% speed.
        If compass is lost during a pulse, reverse half distance to recover.
        Updates self.pitchrate, self.yawrate, self.rollrate.
        @return: True if calibration succeeded.
        """
        CAL_PULSE = 1.0  # seconds

        off = self.get_nav_offset(scr_reg)
        if off is None or off['z'] < 0:
            logger.info("calibrate_rates: compass not visible or target behind, skipping")
            return False

        logger.info(f"calibrate_rates: starting (pit={off['pit']:.1f} yaw={off['yaw']:.1f} roll={off['roll']:.1f})")

        # --- Pitch ---
        self.keys.send('PitchUpButton', hold=CAL_PULSE)
        sleep(0.3)
        new_off = self.get_nav_offset(scr_reg)
        if new_off and new_off['z'] >= 0:
            moved = abs(new_off['pit'] - off['pit'])
            if moved > 2.0:
                self.pitchrate = moved / CAL_PULSE
                logger.info(f"calibrate_rates: pitchrate = {self.pitchrate:.1f} deg/s")
            # Undo the pitch
            self.keys.send('PitchDownButton', hold=CAL_PULSE)
            sleep(0.3)
            off = self.get_nav_offset(scr_reg) or off
        else:
            logger.warning("calibrate_rates: lost compass during pitch cal, recovering")
            recovered = self._cal_recover(scr_reg, 'PitchDownButton', CAL_PULSE)
            if recovered:
                off = recovered
            else:
                logger.warning("calibrate_rates: pitch recovery failed, aborting")
                return False

        # --- Yaw ---
        self.keys.send('YawRightButton', hold=CAL_PULSE)
        sleep(0.3)
        new_off = self.get_nav_offset(scr_reg)
        if new_off and new_off['z'] >= 0:
            moved = abs(new_off['yaw'] - off['yaw'])
            if moved > 1.0:
                self.yawrate = moved / CAL_PULSE
                logger.info(f"calibrate_rates: yawrate = {self.yawrate:.1f} deg/s")
            # Undo the yaw
            self.keys.send('YawLeftButton', hold=CAL_PULSE)
            sleep(0.3)
            off = self.get_nav_offset(scr_reg) or off
        else:
            logger.warning("calibrate_rates: lost compass during yaw cal, recovering")
            recovered = self._cal_recover(scr_reg, 'YawLeftButton', CAL_PULSE)
            if recovered:
                off = recovered
            else:
                logger.warning("calibrate_rates: yaw recovery failed, aborting")
                return False

        # --- Roll ---
        self.keys.send('RollRightButton', hold=CAL_PULSE)
        sleep(0.3)
        new_off = self.get_nav_offset(scr_reg)
        if new_off and new_off['z'] >= 0:
            moved = abs(new_off['roll'] - off['roll'])
            if moved > 5.0:
                self.rollrate = moved / CAL_PULSE
                logger.info(f"calibrate_rates: rollrate = {self.rollrate:.1f} deg/s")
            # Undo the roll
            self.keys.send('RollLeftButton', hold=CAL_PULSE)
            sleep(0.3)
        else:
            logger.warning("calibrate_rates: lost compass during roll cal, recovering")
            self._cal_recover(scr_reg, 'RollLeftButton', CAL_PULSE)

        self.ap_ckb('log', f'Calibrated: pitch={self.pitchrate:.1f} yaw={self.yawrate:.1f} roll={self.rollrate:.1f} deg/s')
        logger.info(f"calibrate_rates: done. pitch={self.pitchrate:.1f} yaw={self.yawrate:.1f} roll={self.rollrate:.1f}")
        return True

    def compass_align(self, scr_reg) -> bool:
        """ Align ship to compass nav target.
        Strategy:
          1) If target behind: pitch flip
          2) If roll > 45deg off centerline: coarse roll to get close
          3) Yaw + Pitch for fine alignment (reliable, no overshoot)
        @return: True if aligned, else False.
        """
        close = 2.0  # degrees -- tight tolerance, SC Assist needs accurate alignment
        if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
            logger.error('align=err1, nav_align not in super or space')
            raise Exception('nav_align not in super or space')

        self.ap_ckb('log+vce', 'Compass Align')
        self.set_speed_50()
        prev_off = None

        align_tries = 0
        max_align_tries = self.config['NavAlignTries']
        max_total_loops = max_align_tries * 5  # safety cap to prevent infinite loop

        for loop in range(max_total_loops):
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

            logger.info(f"Compass: roll={off['roll']:.1f} pit={off['pit']:.1f} yaw={off['yaw']:.1f} z={off['z']}")

            # Target behind -- pitch flip
            if off['z'] < 0:
                if prev_off and prev_off.get('z', 1) < 0 and abs(prev_off['roll'] - off['roll']) < 5:
                    logger.warning("Compass: flip had no effect, waiting 3s.")
                    self.ap_ckb('log', 'Flip had no effect, waiting...')
                    sleep(3)
                    align_tries += 1  # stuck flips count

                pitch_time = 180.0 / self.pitchrate
                logger.info(f"Compass: target behind, pitching up {pitch_time:.1f}s")
                self.ap_ckb('log', 'Target behind, flipping')
                self.keys.send('PitchUpButton', hold=pitch_time)
                sleep(0.5)
                prev_off = off
                continue  # flip itself doesn't count
            prev_off = off

            # Already aligned?
            if abs(off['pit']) < close and abs(off['yaw']) < close:
                self.ap_ckb('log', 'Compass Align complete')
                return True

            # Coarse roll if dot is far off the vertical centerline
            roll_off_centerline = min(abs(off['roll']), 180 - abs(off['roll']))
            if roll_off_centerline > self.COARSE_ROLL_THRESHOLD:
                logger.info(f"Compass: roll {roll_off_centerline:.1f}deg off centerline, coarse roll")
                self.ap_ckb('log', 'Coarse roll')
                off = self._roll_to_centerline(scr_reg, off, close=self.COARSE_ROLL_THRESHOLD)
                if off is None:
                    continue
                if off.get('z', 1) < 0:
                    logger.info("Compass: target went behind during roll, flipping")
                    pitch_time = 180.0 / self.pitchrate
                    self.keys.send('PitchUpButton', hold=pitch_time)
                    sleep(0.5)
                    continue

            # Fine alignment: yaw then pitch -- THIS counts as an alignment try
            align_tries += 1
            logger.info(f"Compass: alignment attempt {align_tries}/{max_align_tries}")

            off = self._yaw_to_center(scr_reg, off, close)
            if off is None:
                continue

            off = self._pitch_to_center(scr_reg, off, close)
            if off is None:
                continue

            # Verify
            logger.info(f"Compass after align: pit={off['pit']:.1f} yaw={off['yaw']:.1f}")
            if abs(off['pit']) < close and abs(off['yaw']) < close:
                self.ap_ckb('log', 'Compass Align complete')
                return True

            logger.info("Compass: not converged, retrying")
            if align_tries >= max_align_tries:
                break

        self.ap_ckb('log+vce', 'Compass Align failed - exhausted all retries')
        return False

    def mnvr_to_target(self, scr_reg):
        """ Maneuver to Target using compass then target before performing a jump."""
        logger.debug('mnvr_to_target entered')

        if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
            logger.error('align() not in sc or space')
            raise Exception('align() not in sc or space')

        # Wait for SCO to finish before aligning (ship uncontrollable during SCO)
        if self.sc_sco_is_active:
            logger.info('mnvr_to_target: SCO active, waiting for it to finish')
            self.ap_ckb('log', 'Waiting for SCO to finish...')
            for _ in range(30):  # max 30s wait
                sleep(1)
                if not self.sc_sco_is_active:
                    break
            sleep(1)  # extra settle time

        self.sun_avoid(scr_reg)

        res = self.compass_align(scr_reg)

        # After compass align, check if target reticle is visible for fine alignment.
        # If only compass is available, compass align is good enough for FSD -- just go.
        tar_off = self.get_target_offset(scr_reg)
        if tar_off:
            self.ap_ckb('log+vce', 'Target Align')
            for i in range(5):
                self.set_speed_25()
                align_res = self.sc_target_align(scr_reg)
                if align_res == ScTargetAlignReturn.Lost:
                    self.set_speed_25()
                    self.compass_align(scr_reg)

                elif align_res == ScTargetAlignReturn.Found:
                    break

                elif align_res == ScTargetAlignReturn.Disengage:
                    break
        else:
            logger.info('mnvr_to_target: no target reticle, compass align is sufficient for FSD')
            self.ap_ckb('log', 'Compass aligned, proceeding to FSD')

        # Throttle zero briefly after alignment, then full speed for FSD
        self.set_speed_0()
        sleep(0.3)
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
                # Neither target nor compass dot found -- likely behind
                none_count += 1
                if none_count >= 3:
                    self.ap_ckb('log', 'Target likely behind us (no dot 3x), pitching up to recover')
                    for _ in range(6):  # max 6x30=180 degrees
                        self.pitch_up_down(30)
                        sleep(0.5)
                        check = self.get_nav_offset(scr_reg)
                        if check:
                            break
                    sleep(1.0)
                    none_count = 0
                else:
                    sleep(0.5)  # brief wait before retry
                continue


            # check for SC Disengage
            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.stop_sco_monitoring()
                return ScTargetAlignReturn.Disengage

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


            # check for SC Disengage
            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.stop_sco_monitoring()
                return ScTargetAlignReturn.Disengage

            # Check if target is outside the target region (behind us) and break loop
            if tar_off2 is None and nav_off2 is None:
                logger.debug("sc_target_align lost target")
                self.ap_ckb('log', 'Target Align failed - lost target.')
                return ScTargetAlignReturn.Lost

        # We are aligned, so define the navigation correction as the current offset. This won't be 100% accurate, but
        # will be within a few degrees.
        if tar_off1 and nav_off1:
            self._nav_cor_x = self._nav_cor_x + nav_off1['x']
            self._nav_cor_y = self._nav_cor_y + nav_off1['y']
        elif tar_off2 and nav_off2:
            self._nav_cor_x = self._nav_cor_x + nav_off2['x']
            self._nav_cor_y = self._nav_cor_y + nav_off2['y']

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

    def honk(self):
        # Do the Discovery Scan (Honk)

        if self.status.get_flag(FlagsAnalysisMode):
            fire_key = 'PrimaryFire' if self.config['DSSButton'] == 'Primary' else 'SecondaryFire'
            if not self.keys.has_binding(fire_key):
                logger.warning(f'honk: no keybinding for {fire_key}, skipping discovery scan')
                self.ap_ckb('log', f'No keybinding for {fire_key}. Skipping honk.')
                return

            logger.debug('position=scanning')
            self.keys.send(fire_key, state=1)
            sleep(7)  # roughly 6 seconds for DSS
            logger.debug('position=scanning complete')
            self.keys.send(fire_key, state=0)
        else:
            self.ap_ckb('log', 'Not in analysis mode. Skipping discovery scan (honk).')

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
    def position(self, scr_reg):
        logger.debug('position')

        self.set_speed_100()

        logger.info("Passing star")

        # Need time to move past Sun for heat to dissipate
        pause_time = 12
        if self.config["EnableRandomness"]:
            pause_time = pause_time + random.randint(0, 3)
        sleep(pause_time)

        logger.info("Maneuvering")

        logger.debug('position=complete')
        return True

    # jump() happens after we are aligned to Target
    # TODO: nees to check for Thargoid interdiction and their wave that would shut us down,
    #       if thargoid, then we wait until reboot and continue on.. go back into FSD and align
    def jump(self, scr_reg):
        logger.debug('jump')

        logger.info("Frameshift Jump")

        # Stop SCO monitoring
        self.stop_sco_monitoring()

        jump_tries = self.config['JumpTries']
        for i in range(jump_tries):

            logger.debug('jump= try:'+str(i))
            if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
                logger.error('Not ready to FSD jump. jump=err1')
                raise Exception('not ready to jump')
            sleep(0.5)
            logger.debug('jump= start fsd')

            # Ensure game window is focused and initiate FSD Jump
            set_focus_elite_window()
            sleep(0.5)
            self.keys.send('HyperSuperCombination')

            res = self.status.wait_for_flag_on(FlagsFsdCharging, 5)
            if not res:
                logger.error('FSD failed to charge.')
                continue

            res = self.status.wait_for_flag_on(FlagsFsdJump, 30)
            if not res:
                logger.warning('FSD failure to start jump timeout.')
                self.mnvr_to_target(scr_reg)  # attempt realign to target
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

            # Start SCO monitoring ready when we drop back to SC.
            self.start_sco_monitoring()

            # We completed the jump
            return True

        logger.error(f'FSD Jump failed {jump_tries} times. jump=err2')
        raise Exception("FSD Jump failure")

        # a set of convience routes to pitch, rotate by specified degress

    def roll_clockwise_anticlockwise(self, deg):
        abs_deg = abs(deg)
        htime = abs_deg/self.rollrate

        if self.speed_demand is None:
            self.set_speed_25()

        # # Using Power calc for roll rate
        # if 0 < abs_deg < 45:
        #     value = self.rollrate * math.pow((abs_deg / 45), (1 / self.roll_factor))
        #     value = min(value, self.rollrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 45 degrees, else use default
        if abs_deg < 45:
            # Roll rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'RollRate' not in speed_demand:
                speed_demand['RollRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['RollRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Roll demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Roll demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are rolling right or left
        if deg > 0.0:
            self.keys.send('RollRightButton', hold=htime)
        else:
            self.keys.send('RollLeftButton', hold=htime)

    def pitch_up_down(self, deg):
        abs_deg = abs(deg)
        htime = abs_deg/self.pitchrate

        if self.speed_demand is None:
            self.set_speed_25()

        # # Using Power calc for pitch rate
        # if 0 < abs_deg < 30:
        #     value = self.pitchrate * math.pow((abs_deg / 30), (1 / self.pitch_factor))
        #     value = min(value, self.pitchrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 30 degrees, else use default
        if abs_deg < 30:
            # Pitch rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'PitchRate' not in speed_demand:
                speed_demand['PitchRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['PitchRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Pitch demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Pitch demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are pitching up or down
        if deg > 0.0:
            self.keys.send('PitchUpButton', hold=htime)
        else:
            self.keys.send('PitchDownButton', hold=htime)

    def yaw_right_left(self, deg):
        """ Yaw in deg. (> 0.0 for yaw right, < 0.0 for yaw left)
        @return: The key hold duration.
        """
        abs_deg = abs(deg)
        htime = abs_deg/self.yawrate

        if self.speed_demand is None:
            self.set_speed_25()

        # # Using Power calc for yaw rate
        # if 0 < abs_deg < 30:
        #     value = self.yawrate * math.pow((abs_deg / 30), (1 / self.yaw_factor))
        #     value = min(value, self.yawrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 30 degrees, else use default
        if abs_deg < 30:
            # Yaw rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'YawRate' not in speed_demand:
                speed_demand['YawRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['YawRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Yaw demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Yaw demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are yawing right or left
        if deg > 0.0:
            self.keys.send('YawRightButton', hold=htime)
        else:
            self.keys.send('YawLeftButton', hold=htime)

    def refuel(self, scr_reg):
        """ Check if refueling needed, ensure correct start type. """
        # Check if we have a fuel scoop
        has_fuel_scoop = self.jn.ship_state()['has_fuel_scoop']

        logger.debug('refuel')
        scoopable_stars = ['F', 'O', 'G', 'K', 'B', 'A', 'M']

        if self.jn.ship_state()['status'] != 'in_supercruise':
            logger.error('refuel=err1')
            return False

        is_star_scoopable = self.jn.ship_state()['star_class'] in scoopable_stars

        if self.jn.ship_state()['fuel_percent'] < self.config['RefuelThreshold'] and is_star_scoopable and has_fuel_scoop:
            logger.debug('refuel= start refuel')
            logger.info("Refueling")
            self.ap_ckb('log', 'Refueling')
            self.update_ap_status("Refueling")

            # mnvr into position
            self.set_speed_100()
            sleep(5)
            self.set_speed_50()
            sleep(1.7)
            self.set_speed_0(repeat=3)

            self.refuel_cnt += 1

            # The log will not reflect a FuelScoop until first 5 tons filled, then every 5 tons until complete
            #if we don't scoop first 5 tons with 40 sec break, since not scooping or not fast enough or not at all, then abort
            startime = time.time()
            while not self.jn.ship_state()['is_scooping'] and not self.jn.ship_state()['fuel_percent'] == 100:
                # check if we are being interdicted
                interdicted = self.interdiction_check()
                if interdicted:
                    # Continue journey after interdiction
                    self.set_speed_0()

                if ((time.time()-startime) > int(self.config['FuelScoopTimeOut'])):
                    logger.info("Refueling abort, insufficient scooping")
                    return False

            logger.debug('refuel= wait for refuel')

            # We started fueling, so lets give it another timeout period to fuel up
            startime = time.time()
            while not self.jn.ship_state()['fuel_percent'] == 100:
                # check if we are being interdicted
                interdicted = self.interdiction_check()
                if interdicted:
                    # Continue journey after interdiction
                    self.set_speed_0()

                if ((time.time()-startime) > int(self.config['FuelScoopTimeOut'])):
                    logger.info("Refueling abort, insufficient scooping")
                    return True
                sleep(1)

            logger.debug('refuel=complete')
            return True

        elif is_star_scoopable == False:
            self.ap_ckb('log', 'Skip refuel - not a fuel star')
            logger.debug('refuel= needed, unsuitable star')
            self.pitch_up_down(20)
            return False

        elif self.jn.ship_state()['fuel_percent'] >= self.config['RefuelThreshold']:
            self.ap_ckb('log', 'Skip refuel - fuel level okay')
            logger.debug('refuel= not needed')
            return False

        elif not has_fuel_scoop:
            self.ap_ckb('log', 'Skip refuel - no fuel scoop fitted')
            logger.debug('No fuel scoop fitted.')
            self.pitch_up_down(20)
            return False

        else:
            self.pitch_up_down(15)  # if not refueling pitch up somemore so we won't heat up
            return False

    def waypoint_undock_seq(self):
        self.update_ap_status("Executing Undocking/Launch")

        # Store current location (on planet or in space)
        on_planet = self.status.get_flag(FlagsHasLatLong)
        on_orbital_construction_site = (self.jn.ship_state()['exp_station_type'] == EDJournal.StationType.SpaceConstructionDepot or
                                       self.jn.ship_state()['exp_station_type'] == EDJournal.StationType.ColonisationShip)
        fleet_carrier = self.jn.ship_state()['exp_station_type'] == EDJournal.StationType.FleetCarrier
        squadron_fleet_carrier = self.jn.ship_state()['exp_station_type'] == EDJournal.StationType.SquadronCarrier
        starport_outpost = not on_planet and not on_orbital_construction_site and not fleet_carrier and not squadron_fleet_carrier

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

                # need to wait until undock complete, that is when we are back in_space
                while self.jn.ship_state()['status'] != 'in_space':
                    sleep(1)

                if on_orbital_construction_site:
                    # Construction site: no autodock departure, just wait 4s then maneuver
                    self.ap_ckb('log+vce', 'Maneuvering away from construction site')
                    sleep(4)
                    self.set_speed_25()
                    self.keys.send('PitchUpButton', hold=3.0)
                    sleep(0.5)
                    self.keys.send('UseBoostJuice')
                    sleep(8)
                    self.set_speed_100()
                    self.keys.send('PitchDownButton', hold=3.0)
                    self.ap_ckb('log', 'Waiting for masslock to clear...')
                    for _ in range(60):  # max 60s
                        if not self.status.get_flag(FlagsFsdMassLocked):
                            break
                        sleep(1)
                    self.update_ap_status("Undock Complete, accelerating")
                    self.sc_engage(True)

                else:
                    # Station/outpost/FC: wait for autodock to finish departure
                    for _ in range(30):  # max 30s
                        if not self.status.get_flag(FlagsLandingGearDown):
                            break
                        sleep(1)
                    logger.info("Undock: landing gear retracted, ship has full control")

                    if fleet_carrier or squadron_fleet_carrier:
                        self.ap_ckb('log+vce', 'Maneuvering')
                        self.pitch_up_down(self.config['FCDepartureAngle'])
                        self.update_ap_status("Undock Complete, accelerating")
                        self.sc_engage(True)
                        self.ap_ckb('log', 'Flying for configured FC departure time.')
                        sleep(self.config['FCDepartureTime'])

                    if starport_outpost:
                        self.update_ap_status("Undock Complete, accelerating")
                        self.sc_engage(True)

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

                # need to wait until undock complete, that is when we are back in_space
                while self.jn.ship_state()['status'] != 'in_space':
                    sleep(1)
                self.update_ap_status("Undock Complete, accelerating")

            elif self.status.get_flag(FlagsLanded):
                # We are on planet surface (not docked at planet landing pad)
                # Hold UP for takeoff
                self.keys.send('UpThrustButton', hold=6)
                self.keys.send('LandingGearToggle')
                self.update_ap_status("Takeoff Complete, accelerating")

            # Undocked or off the surface, so leave planet
            self.set_speed_50()
            # The pitch rates are defined in SC, not normal flights, so bump this up a bit
            self.pitch_up_down(90 * 1.25)

            # Engage Supercruise
            self.sc_engage(True)

            # Enable SCO. If SCO not fitted, this will do nothing.
            self.keys.send('UseBoostJuice')

            # Wait until out of orbit.
            res = self.status.wait_for_flag_off(FlagsHasLatLong, timeout=60)
            # TODO - do we need to check if we never leave orbit?

            # Disable SCO. If SCO not fitted, this will do nothing.
            self.keys.send('UseBoostJuice')

    def sc_engage(self, boost: bool) -> bool:
        """ Engages supercruise, then returns us to 50% speed, unless we are in SC already.
        """
        # Check if we are already in SC
        if self.status.get_flag(FlagsSupercruise):
            # Start SCO monitoring
            self.start_sco_monitoring()
            return True

        self.set_speed_100()

        # While Mass Locked, boost up to 3 times to clear station
        boost_count = 0
        while self.status.get_flag(FlagsFsdMassLocked):
            if boost and boost_count < 3:
                self.keys.send('UseBoostJuice')
                boost_count += 1
            sleep(1)

        # Engage Supercruise
        self.keys.send('Supercruise')

        # Start SCO monitoring
        self.start_sco_monitoring()

        # Wait for jump to supercruise
        while not self.status.get_flag(FlagsFsdJump):
            sleep(1)

        # Wait for supercruise
        self.status.wait_for_flag_on(FlagsSupercruise, timeout=30)

        # Short SCO burst to get away from planet gravity well
        self.keys.send('UseBoostJuice')
        sleep(3)
        self.keys.send('UseBoostJuice')

        # Revert to 50%
        self.set_speed_50()
        sleep(1)

        # Calibrate actual turn rates in SC at 50% speed
        self.calibrate_rates(self.scrReg)

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

        # Discovery scan (honk)
        self.honk_thread = threading.Thread(target=self.honk, daemon=True)
        self.honk_thread.start()

        # Sun avoidance
        self.sun_avoid(scr_reg)

        self.update_ap_status("Maneuvering")
        self.position(scr_reg)
        self.set_speed_0()

    def supercruise_to_station(self, scr_reg, station_name: str) -> bool:
        """ Supercruise to the specified target, which may be a station, FC, body, signal source, etc.
        Returns True if we travel successfully travel there, else False. """
        # If waypoint file has a Station Name associated then attempt targeting it
        self.update_ap_status(f"Targeting Station: {station_name}")

        # if we are starting the waypoint docked at a station, we need to undock first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage(False)

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
        self.sc_engage(False)
        self.jn.ship_state()['interdicted'] = False

        # Verify we are actually in supercruise before proceeding
        if self.jn.ship_state()['status'] != 'in_supercruise':
            self.ap_ckb('log', 'SC Assist aborted - not in supercruise')
            logger.warning(f"sc_assist: not in supercruise, status={self.jn.ship_state()['status']}")
            return

        # Sun avoidance first (pitch up if sun ahead after FSD drop)
        self.sun_avoid(scr_reg)

        # Align to target using compass
        aligned = self.compass_align(scr_reg)
        if not aligned:
            self.ap_ckb('log', 'SC Assist: compass align failed, retrying once...')
            sleep(2)
            aligned = self.compass_align(scr_reg)
            if not aligned:
                self.ap_ckb('log', 'SC Assist aborted - could not align to target')
                logger.warning("sc_assist: compass_align failed after retry, aborting")
                return

        # Throttle zero after alignment, activate SC Assist, then 75%
        self.set_speed_0()
        sleep(0.5)
        self.ap_ckb('log', 'Activating SC Assist via Nav Panel')
        self.nav_panel.activate_sc_assist()
        sleep(0.5)
        self.keys.send('SetSpeed75')
        sc_assist_cruising = False  # wait for throttle text to clear first

        # Wait for SC Assist to fly us there and drop us out
        self.ap_ckb('log', 'Waiting for SC Assist to reach destination...')
        self.start_sco_monitoring()
        sleep(5)  # let SC Assist settle and throttle text disappear
        sc_assist_cruising = True
        while True:
            sleep(2.5)

            if self.jn.ship_state()['status'] != 'in_supercruise':
                # Dropped from supercruise (SC Assist completed or glide)
                if self.status.get_flag2(Flags2GlideMode):
                    logger.debug("Gliding")
                    self.status.wait_for_flag2_off(Flags2GlideMode, 30)
                else:
                    logger.debug("No longer in supercruise - SC Assist dropped us")
                self.stop_sco_monitoring()
                break

            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.stop_sco_monitoring()
                break

            # Only check occlusion when SC Assist is cruising at 75%
            if sc_assist_cruising and self.is_target_occluded(scr_reg):
                sc_assist_cruising = False
                self.ap_ckb('log', 'Target obscured by body -- evading')
                logger.info("sc_assist: occlusion warning text detected")
                # Deactivate SC Assist
                self.keys.send('SetSpeed25')
                # Pitch up to clear the body
                pitch_time = 45.0 / self.pitchrate
                self.keys.send('PitchUpButton', hold=pitch_time)
                # Fly past the body
                self.set_speed_100()
                sleep(15)
                # Slow down for realign
                self.set_speed_25()
                self.compass_align(scr_reg)
                # Re-engage SC Assist
                self.keys.send('SetSpeed75')
                sc_assist_cruising = True
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
            sleep(4)  # wait for the journal to catch up

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
                self.dock()
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
            if self.jn.ship_state()['status'] == 'in_supercruise':
                cur_star_system = self.jn.ship_state()['cur_star_system']
                if cur_star_system != self._prev_star_system:
                    self.update_ap_status("DSS Scan")
                    self.ap_ckb('log', 'DSS Scan: '+cur_star_system)
                    set_focus_elite_window()
                    self.honk()
                    self._prev_star_system = cur_star_system
                    self.update_ap_status("Idle")

    # raising an exception to the engine loop thread, so we can terminate its execution
    #  if thread was in a sleep, the exception seems to not be delivered
    def ctype_async_raise(self, thread_obj, exception):
        found = False
        target_tid = 0
        for tid, tobj in threading._active.items():
            if tobj is thread_obj:
                found = True
                target_tid = tid
                break

        if not found:
            raise ValueError("Invalid thread object")

        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                         ctypes.py_object(exception))
        # ref: http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
        if ret == 0:
            raise ValueError("Invalid thread ID")
        elif ret > 1:
            # Huh? Why would we notify more than one threads?
            # Because we punch a hole into C level interpreter.
            # So it is better to clean up the mess.
            ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    #
    # Setter routines for state variables
    #
    def set_sc_assist(self, enable=True):
        if enable == False and self.sc_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.sc_assist_enabled = enable

    def set_waypoint_assist(self, enable=True):
        if enable == False and self.waypoint_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.waypoint_assist_enabled = enable

    def set_dss_assist(self, enable=True):
        if enable == False and self.dss_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
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

            # TODO - Enable for test
            # self.start_sco_monitoring()

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

            if self.sc_assist_enabled == True:
                logger.debug("Running sc_assist")
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.update_ap_status("SC to Target")
                    self.sc_assist(self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    print("Trapped generic:"+str(e))
                    logger.debug("SC Assist trapped generic:"+str(e))
                    traceback.print_exc()

                self.stop_sco_monitoring()
                logger.debug("Completed sc_assist")
                self.sc_assist_enabled = False
                self.ap_ckb('sc_stop')
                self.update_overlay()

            elif self.waypoint_assist_enabled == True:
                logger.debug("Running waypoint_assist")

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
                    print("Trapped generic:"+str(e))
                    logger.debug("Waypoint Assist trapped generic:"+str(e))
                    traceback.print_exc()

                self.stop_sco_monitoring()
                self.waypoint_assist_enabled = False
                self.ap_ckb('waypoint_stop')
                self.update_overlay()

            elif self.dss_assist_enabled == True:
                logger.debug("Running dss_assist")
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.dss_assist()
                except EDAP_Interrupt:
                    logger.debug("Stopping DSS Assist")
                except Exception as e:
                    print("Trapped generic:" + str(e))
                    logger.debug("DSS Assist trapped generic:" + str(e))
                    traceback.print_exc()

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

    def ship_tst_pitch(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.pitch_up_down(angle)

    def ship_tst_pitch_new(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        self.ap_ckb('log', "Starting Pitch Calibration.")
        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            # sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['PitchRate'] = dict()

        test_time = 0.05
        delta_int = 0.0
        for targ_ang in [5, 10, 20, 40, 80, 160]:
            while 1:
                set_focus_elite_window()
                off = self.get_target_offset(self.scrReg)
                if not off:
                    print(f"Target lost")
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('target')
                    self.overlay.overlay_remove_floating_text('target')
                    self.overlay.overlay_remove_floating_text('target_occ')
                    self.overlay.overlay_remove_floating_text('target_rpy')
                    self.overlay.overlay_paint()

                if off['pit'] > 0:
                    self.keys.send('PitchUpButton', hold=test_time)
                else:
                    self.keys.send('PitchDownButton', hold=test_time)

                sleep(1)

                off2 = self.get_target_offset(self.scrReg)
                if not off2:
                    print(f"Target lost")
                    break

                delta = abs(off2['pit'] - off['pit'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.04
                rate = round(delta / test_time, 2)
                rate = min(rate, self.pitchrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['PitchRate'][delta_int] = rate

                    print(f"Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 30 deg
        if len(ship_type[self.speed_demand]['PitchRate']) > 0:
            ship_type[self.speed_demand]['PitchRate'][300] = self.pitchrate
            self.ap_ckb('log', f"Default: Pitch Angle: 30: Rate: {self.pitchrate}")

        self.ap_ckb('log', "Completed Pitch Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def ship_tst_pitch_calc_power(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        # sleep(0.25)
        # # self.set_speed_50()
        # self.pitch_up_down(angle)

        target_align_outer_lim = 1.0
        target_align_inner_lim = 0.5

        off = None
        tar_off1 = None
        tar_off2 = None

        # Try to get the target 5 times before quiting
        for i in range(5):
            # Check Target and Compass
            tar_off1 = self.get_target_offset(self.scrReg)
            if tar_off1:
                # Target detected
                off = tar_off1

            # Quit loop if we found Target or Compass
            if off:
                break

        # We have Target or Compass. Are we close to Target?
        while (abs(off['pit']) > target_align_outer_lim):

            target_align_outer_lim = target_align_inner_lim  # Keep aligning until we are within this lower range.

            # Clear the overlays before moving
            if self.debug_overlay:
                self.overlay.overlay_remove_rect('target')
                self.overlay.overlay_remove_floating_text('target')
                self.overlay.overlay_remove_floating_text('target_occ')
                self.overlay.overlay_remove_floating_text('target_rpy')
                self.overlay.overlay_paint()

            # Calc pitch time based on nav point location
            logger.debug(f"sc_target_align before: pit: {off['pit']} roll: {off['roll']} ")

            p_deg = 0.0
            if abs(off['pit']) > target_align_outer_lim:
                p_deg = off['pit']
                self.pitch_up_down(p_deg)

            # Wait for ship to finish moving and picture to stabilize
            sleep(2.0)

            # Check Target and Compass
            tar_off2 = self.get_target_offset(self.scrReg)
            if tar_off2:
                off = tar_off2
                logger.debug(f"sc_target_align after: pit:{off['pit']} roll: {off['roll']}")

            if tar_off1 and tar_off2:
                # Check diff from before and after movement
                pit_delta = tar_off2['pit'] - tar_off1['pit']
                if ((tar_off1['pit'] < 0.0 and tar_off2['pit'] > target_align_outer_lim) or
                        (tar_off1['pit'] > 0.0 and tar_off2['pit'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Pitch correction gone too far {round(abs(pit_delta),2)} > {round(abs(tar_off1['pit']),2) + target_align_outer_lim}. Reducing Pitch Factor.")
                    self.ap_ckb('update_ship_cfg')

            if tar_off2:
                # Store current offsets
                tar_off1 = tar_off2.copy()

    def ship_tst_roll(self, angle: float):
        """ Performs a ship roll test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the roll value.
        If the ship rotates too much, increase the roll value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.roll_clockwise_anticlockwise(angle)

    def ship_tst_roll_new(self, angle: float):
        """ Performs a ship roll test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the roll value.
        If the ship rotates too much, increase the roll value.
        """
        self.ap_ckb('log', "Starting Roll Calibration.")
        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            #sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['RollRate'] = dict()

        test_time = 0.05
        delta_int = 0.0
        for targ_ang in [40, 80, 160, 320]:
            while 1:
                set_focus_elite_window()
                off = self.get_nav_offset(self.scrReg)
                if not off:
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('compass')
                    self.overlay.overlay_remove_floating_text('compass')
                    self.overlay.overlay_remove_floating_text('nav')
                    self.overlay.overlay_remove_floating_text('nav_beh')
                    self.overlay.overlay_remove_floating_text('compass_rpy')
                    self.overlay.overlay_paint()

                if off['roll'] > 0:
                    self.keys.send('RollRightButton', hold=test_time)
                else:
                    self.keys.send('RollLeftButton', hold=test_time)

                sleep(1)

                off2 = self.get_nav_offset(self.scrReg)
                if not off2:
                    break

                delta = abs(off2['roll'] - off['roll'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.03
                rate = round(delta / test_time, 2)
                rate = min(rate, self.rollrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['RollRate'][delta_int] = rate

                    print(f"Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 45 deg
        if len(ship_type[self.speed_demand]['RollRate']) > 0:
            ship_type[self.speed_demand]['RollRate'][450] = self.rollrate
            self.ap_ckb('log', f"Default: Roll Angle: 45: Rate: {self.rollrate}")

        self.ap_ckb('log', "Completed Roll Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def ship_tst_yaw(self, angle: float):
        """ Performs a ship yaw test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the yaw value.
        If the ship rotates too much, increase the yaw value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.yaw_right_left(angle)

    def ship_tst_yaw_new(self, angle: float):
        """ Performs a ship yaw test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the yaw value.
        If the ship rotates too much, increase the yaw value.
        """
        self.ap_ckb('log', "Starting Yaw Calibration.")

        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            # sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['YawRate'] = dict()

        test_time = 0.07
        delta_int = 0.0
        for targ_ang in [5, 10, 20, 40, 80, 160]:
            while 1:
                set_focus_elite_window()
                off = self.get_target_offset(self.scrReg)
                if not off:
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('target')
                    self.overlay.overlay_remove_floating_text('target')
                    self.overlay.overlay_remove_floating_text('target_occ')
                    self.overlay.overlay_remove_floating_text('target_rpy')
                    self.overlay.overlay_paint()

                if off['yaw'] > 0:
                    self.keys.send('YawRightButton', hold=test_time)
                else:
                    self.keys.send('YawLeftButton', hold=test_time)

                sleep(1)

                off2 = self.get_target_offset(self.scrReg)
                if not off2:
                    break

                delta = abs(off2['yaw'] - off['yaw'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.05
                rate = round(delta / test_time, 2)
                rate = min(rate, self.yawrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['YawRate'][delta_int] = rate

                    print(f"Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 30 deg
        if len(ship_type[self.speed_demand]['YawRate']) > 0:
            ship_type[self.speed_demand]['YawRate'][300] = self.yawrate
            self.ap_ckb('log', f"Default: Yaw Angle: 30: Rate: {self.yawrate}")

        self.ap_ckb('log', "Completed Yaw Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def set_speed_0(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed0'
        else:
            self.speed_demand = 'Speed0'

        self.keys.send('SetSpeedZero', repeat)

    def set_speed_25(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed25'
        else:
            self.speed_demand = 'Speed25'

        try:
            self.keys.send('SetSpeed25', repeat)
        except Exception:
            # SetSpeed25 not bound -- fall back to 50%
            logger.warning("SetSpeed25 not bound, falling back to SetSpeed50")
            self.set_speed_50(repeat)

    def set_speed_50(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed50'
        else:
            self.speed_demand = 'Speed50'

        self.keys.send('SetSpeed50', repeat)

    def set_speed_100(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed100'
        else:
            self.speed_demand = 'Speed100'

        self.keys.send('SetSpeed100', repeat)

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
                    print(f"Deleting file: '{file_path}'")
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
    ed_ap.pitchrate = 16.0
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
