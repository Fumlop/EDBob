from __future__ import annotations

import json
from os import environ, listdir
import os
from os.path import getmtime, isfile, join
from time import sleep
from typing import Any, final
from xml.etree.ElementTree import parse

import win32gui
import xmltodict

from src.screen.Screen import set_focus_elite_window
from src.core import directinput
from src.core.EDlogger import logger

"""
Description:  Pulls the keybindings for specific controls from the ED Key Bindings file, this class also
  has method for sending a key to the display that has focus (so must have ED with focus)

Constraints:  This file will use the latest modified *.binds file
"""


@final
class EDKeys:

    def __init__(self, cb):
        self.ap_ckb = cb
        self.key_mod_delay = 0.01  # Delay for key modifiers to ensure modifier is detected before/after the key
        self.key_def_hold_time = 0.2  # Default hold time for a key press
        self.key_repeat_delay = 0.1  # Delay between key press repeats
        self.activate_window = True
        self._last_focus_check = 0  # timestamp of last focus check

        self.keys_to_obtain = [
            # Flight
            'YawLeftButton',
            'YawRightButton',
            'RollLeftButton',
            'RollRightButton',
            'PitchUpButton',
            'PitchDownButton',
            'SetSpeedZero',
            'SetSpeed25',
            'SetSpeed50',
            'SetSpeed75',
            'SetSpeed100',
            'UpThrustButton',
            'UseBoostJuice',
            'LandingGearToggle',
            # Navigation
            'HyperSuperCombination',
            'Supercruise',
            'SelectTarget',
            'TargetNextRouteSystem',
            'GalaxyMapOpen',
            'SystemMapOpen',
            # UI
            'FocusLeftPanel',
            'UIFocus',
            'UI_Up',
            'UI_Down',
            'UI_Left',
            'UI_Right',
            'UI_Select',
            'UI_Back',
            'CycleNextPanel',
            'CyclePreviousPanel',
            'HeadLookReset',
            # Power
            'IncreaseEnginesPower',
            'IncreaseWeaponsPower',
            'IncreaseSystemsPower',
            # Combat (optional, used by some assists)
            'DeployHeatSink',
            'DeployHardpointToggle',
            'PrimaryFire',
            'SecondaryFire',
            # Exploration (optional)
            'ExplorationFSSEnter',
            'ExplorationFSSQuit',
            'MouseReset',
            'CamZoomIn',
            'CamTranslateForward',
            'CamTranslateRight',
            'OrderAggressiveBehaviour',
        ]

        # Hardcoded fallback keys -- used when a binding is missing from the .binds file.
        # These match common ED defaults. Override by setting the key in ED options.
        self._fallback_keys = {
            'YawLeftButton':        {'key': directinput.SCANCODE['Key_Numpad_4'], 'mods': []},
            'YawRightButton':       {'key': directinput.SCANCODE['Key_Numpad_6'], 'mods': []},
            'RollLeftButton':       {'key': directinput.SCANCODE['Key_A'], 'mods': []},
            'RollRightButton':      {'key': directinput.SCANCODE['Key_D'], 'mods': []},
            'PitchUpButton':        {'key': directinput.SCANCODE['Key_Numpad_8'], 'mods': []},
            'PitchDownButton':      {'key': directinput.SCANCODE['Key_Numpad_2'], 'mods': []},
            'SetSpeedZero':         {'key': directinput.SCANCODE['Key_LeftShift'], 'mods': []},
            'SetSpeed50':           {'key': directinput.SCANCODE['Key_Y'], 'mods': []},
            'SetSpeed100':          {'key': directinput.SCANCODE['Key_C'], 'mods': []},
            'UpThrustButton':       {'key': directinput.SCANCODE['Key_R'], 'mods': []},
            'UseBoostJuice':        {'key': directinput.SCANCODE['Key_Tab'], 'mods': []},
            'LandingGearToggle':    {'key': directinput.SCANCODE['Key_L'], 'mods': []},
            'HyperSuperCombination': {'key': directinput.SCANCODE['Key_J'], 'mods': []},
            'Supercruise':          {'key': directinput.SCANCODE['Key_Numpad_Add'], 'mods': []},
            'SelectTarget':         {'key': directinput.SCANCODE['Key_T'], 'mods': []},
            'TargetNextRouteSystem': {'key': directinput.SCANCODE['Key_K'], 'mods': []},
            'GalaxyMapOpen':        {'key': directinput.SCANCODE['Key_PageUp'], 'mods': []},
            'SystemMapOpen':        {'key': directinput.SCANCODE['Key_PageDown'], 'mods': []},
            'FocusLeftPanel':       {'key': directinput.SCANCODE['Key_1'], 'mods': []},
            'UIFocus':              {'key': directinput.SCANCODE['Key_5'], 'mods': []},
            'UI_Up':                {'key': directinput.SCANCODE['Key_W'], 'mods': []},
            'UI_Down':              {'key': directinput.SCANCODE['Key_S'], 'mods': []},
            'UI_Left':              {'key': directinput.SCANCODE['Key_A'], 'mods': []},
            'UI_Right':             {'key': directinput.SCANCODE['Key_D'], 'mods': []},
            'UI_Select':            {'key': directinput.SCANCODE['Key_Space'], 'mods': []},
            'UI_Back':              {'key': directinput.SCANCODE['Key_Backspace'], 'mods': []},
            'CycleNextPanel':       {'key': directinput.SCANCODE['Key_E'], 'mods': []},
            'CyclePreviousPanel':   {'key': directinput.SCANCODE['Key_Q'], 'mods': []},
            'HeadLookReset':        {'key': directinput.SCANCODE['Key_7'], 'mods': []},
            'IncreaseEnginesPower': {'key': directinput.SCANCODE['Key_UpArrow'], 'mods': []},
            'IncreaseWeaponsPower': {'key': directinput.SCANCODE['Key_RightArrow'], 'mods': []},
            'IncreaseSystemsPower': {'key': directinput.SCANCODE['Key_LeftArrow'], 'mods': []},
            'DeployHardpointToggle': {'key': directinput.SCANCODE['Key_U'], 'mods': []},
        }

        self.keys = self.get_bindings()
        self.bindings = self.get_bindings_dict()

        # Apply fallbacks for any missing keys
        for key_name, fallback in self._fallback_keys.items():
            if key_name not in self.keys:
                self.keys[key_name] = fallback
                logger.info(f"Using fallback key for '{key_name}': {self.reversed_dict.get(fallback['key'], '?')}")

        self.missing_keys = []
        # We want to log the keyboard name instead of just the key number so we build a reverse dictionary
        # so we can look up the name also
        self.reversed_dict = {value: key for key, value in directinput.SCANCODE.items()}

        # dump config to log
        for key in self.keys_to_obtain:
            try:
                # lookup the keyname in the directinput.SCANCODE reverse dictionary and output that key name
                keyname = self.reversed_dict.get(self.keys[key]['key'], "Key not found")
                keymod = " "
                # if key modifier, then look up that modifier name also
                if len(self.keys[key]['mods']) != 0:
                    keymod = self.reversed_dict.get(self.keys[key]['mods'][0], " ")

                logger.info('\tget_bindings_<{}>={} Key: <{}> Mod: <{}>'.format(key, self.keys[key], keyname, keymod))
                if key not in self.keys:
                    self.ap_ckb('log',
                                f"WARNING: \tget_bindings_<{key}>= does not have a valid keyboard keybind {keyname}.")
                    logger.warning(
                        "\tget_bindings_<{}>= does not have a valid keyboard keybind {}".format(key, keyname).upper())
                    self.missing_keys.append(key)
            except Exception as e:
                self.ap_ckb('log', f"WARNING: \tget_bindings_<{key}>= does not have a valid keyboard keybind.")
                logger.warning("\tget_bindings_<{}>= does not have a valid keyboard keybind.".format(key).upper())
                self.missing_keys.append(key)

        # Check for key collisions with the keys EDAP uses.
        for key in self.keys_to_obtain:
            if key in self.missing_keys:
                continue
            collisions = self.get_collisions(key)
            if len(collisions) > 1:
                # lookup the keyname in the directinput.SCANCODE reverse dictionary and output that key name
                keyname = self.reversed_dict.get(self.keys[key].get('key'), "Key not found")
                warn_text = (f"Key '{keyname}' is used for the following bindings: {collisions}. "
                             "This MAY causes issues when using EDAP. Monitor and adjust accordingly.")
                self.ap_ckb('log', f"WARNING: {warn_text}")
                logger.warning(f"{warn_text}")

        # Check if the hotkeys are used in ED
        binding_name = self.check_hotkey_in_bindings('Key_End')
        if binding_name != "":
            warn_text = (f"Hotkey 'Key_End' is used in the ED keybindings for '{binding_name}'. Recommend changing in"
                         f" ED to another key to avoid EDAP accidentally being triggered.")
            self.ap_ckb('log', f"WARNING: {warn_text}")
            logger.warning(f"{warn_text}")

        binding_name = self.check_hotkey_in_bindings('Key_Insert')
        if binding_name != "":
            warn_text = (f"Hotkey 'Key_Insert' is used in the ED keybindings for '{binding_name}'. Recommend changing in"
                         f" ED to another key to avoid EDAP accidentally being triggered.")
            self.ap_ckb('log', f"WARNING: {warn_text}")
            logger.warning(f"{warn_text}")

        binding_name = self.check_hotkey_in_bindings('Key_PageUp')
        if binding_name != "":
            warn_text = (f"Hotkey 'Key_PageUp' is used in the ED keybindings for '{binding_name}'. Recommend changing in"
                         f" ED to another key to avoid EDAP accidentally being triggered.")
            self.ap_ckb('log', f"WARNING: {warn_text}")
            logger.warning(f"{warn_text}")

        binding_name = self.check_hotkey_in_bindings('Key_Home')
        if binding_name != "":
            warn_text = (f"Hotkey 'Key_Home' is used in the ED keybindings for '{binding_name}'. Recommend changing in"
                         f" ED to another key to avoid EDAP accidentally being triggered.")
            self.ap_ckb('log', f"WARNING: {warn_text}")
            logger.warning(f"{warn_text}")

    def get_bindings(self) -> dict[str, Any]:
        """Returns a dict struct with the direct input equivalent of the necessary elite keybindings"""
        direct_input_keys = {}
        latest_bindings = self.get_latest_keybinds()
        if not latest_bindings:
            return {}
        bindings_tree = parse(latest_bindings)
        bindings_root = bindings_tree.getroot()

        for item in bindings_root:
            if item.tag in self.keys_to_obtain:
                key = None
                mods = []
                hold = None
                # Check primary
                if item[0].attrib['Device'].strip() == "Keyboard":
                    key = item[0].attrib['Key']
                    for modifier in item[0]:
                        if modifier.tag == "Modifier":
                            mods.append(modifier.attrib['Key'])
                        elif modifier.tag == "Hold":
                            hold = True
                # Check secondary (and prefer secondary)
                if item[1].attrib['Device'].strip() == "Keyboard":
                    key = item[1].attrib['Key']
                    mods = []
                    hold = None
                    for modifier in item[1]:
                        if modifier.tag == "Modifier":
                            mods.append(modifier.attrib['Key'])
                        elif modifier.tag == "Hold":
                            hold = True
                # Prepare final binding
                binding: None | dict[str, Any] = None
                try:
                    if key is not None:
                        binding = {}
                        binding['key'] = directinput.SCANCODE[key]
                        binding['mods'] = []
                        for mod in mods:
                            binding['mods'].append(directinput.SCANCODE[mod])
                        if hold is not None:
                            binding['hold'] = True
                except KeyError:
                    print("Unrecognised key '" + (
                        json.dumps(binding) if binding else '?') + "' for bind '" + item.tag + "'")
                if binding is not None:
                    direct_input_keys[item.tag] = binding

        if len(list(direct_input_keys.keys())) < 1:
            return {}
        else:
            return direct_input_keys

    def get_bindings_dict(self) -> dict[str, Any]:
        """Returns a dict of all the elite keybindings.
        @return: A dictionary of the keybinds file.
        Example:
        {
        'Root': {
            'YawLeftButton': {
                'Primary': {
                    '@Device': 'Keyboard',
                    '@Key': 'Key_A'
                },
                'Secondary': {
                    '@Device': '{NoDevice}',
                    '@Key': ''
                }
            }
        }
        }
        """
        latest_bindings = self.get_latest_keybinds()
        if not latest_bindings:
            return {}

        try:
            with open(latest_bindings, 'r') as file:
                my_xml = file.read()
                my_dict = xmltodict.parse(my_xml)
                return my_dict

        except OSError as e:
            logger.error(f"OS Error reading Elite Dangerous bindings file: {latest_bindings}.")
            raise Exception(f"OS Error reading Elite Dangerous bindings file: {latest_bindings}.")

    def check_hotkey_in_bindings(self, key_name: str) -> str:
        """ Check for the action keys. """
        ret = []
        for key, value in self.bindings['Root'].items():
            if type(value) is dict:
                primary = value.get('Primary', None)
                if primary is not None:
                    if primary['@Key'] == key_name:
                        ret.append(f"{key} (Primary)")
                secondary = value.get('Secondary', None)
                if secondary is not None:
                    if secondary['@Key'] == key_name:
                        ret.append(f"{key} (Secondary)")
        return " and ".join(ret)

    # Note:  this routine will grab the *.binds file which is the latest modified
    def get_latest_keybinds(self):
        path_bindings = environ['LOCALAPPDATA'] + "\Frontier Developments\Elite Dangerous\Options\Bindings"
        try:
            list_of_bindings = [join(path_bindings, f) for f in listdir(path_bindings) if
                                isfile(join(path_bindings, f)) and f.endswith('.binds')]
        except FileNotFoundError as e:
            return None

        if not list_of_bindings:
            return None
        latest_bindings = max(list_of_bindings, key=getmtime)
        logger.info(f'Latest keybindings file:{latest_bindings}')
        return latest_bindings

    def send_key(self, type, key):
        if type == 'Up':
            directinput.ReleaseKey(key)
        else:
            directinput.PressKey(key)

    def has_binding(self, key_binding: str) -> bool:
        """Check if a keybinding exists."""
        return self.keys.get(key_binding) is not None

    def send(self, key_binding, hold=None, repeat=1, repeat_delay=None, state=None):
        """ Send a key based on the defined keybind
        @param key_binding: The key bind name (i.e. UseBoostJuice).
        @param hold: The time to hold the key down in seconds.
        @param repeat: Number of times to repeat the key.
        @param repeat_delay: Time delay in seconds between repeats. If None, uses the default repeat delay.
        @param state: Key state:
            None - press and release (default).
            1 - press (but don't release).
            0 - release (a previous press state).
        """
        key = self.keys.get(key_binding)
        if key is None:
            logger.warning('SEND=NONE !!!!!!!!')
            self.ap_ckb('log', f"WARNING: Unable to retrieve keybinding for {key_binding}.")
            raise Exception(
                f"Unable to retrieve keybinding for {key_binding}. Advise user to check game settings for keyboard bindings.")

        key_name = self.reversed_dict.get(key['key'], "Key not found")
        logger.info(f"send: {key_binding} -> {key_name} (scancode={key['key']}, hold={hold}, state={state})")

        # Focus Elite window before sending keys (only check every 5 seconds to avoid disrupting holds)
        import time as _time
        if self.activate_window and (_time.time() - self._last_focus_check) > 5.0:
            self._last_focus_check = _time.time()
            set_focus_elite_window()

        for i in range(repeat):

            if state is None or state == 1:
                for mod in key['mods']:
                    directinput.PressKey(mod)
                    sleep(self.key_mod_delay)

                directinput.PressKey(key['key'])

            if state is None:
                if hold:
                    if hold > 0.0:
                        sleep(hold)
                else:
                    if self.key_def_hold_time > 0.0:
                        sleep(self.key_def_hold_time)

            if 'hold' in key:
                sleep(0.1)

            if state is None or state == 0:
                directinput.ReleaseKey(key['key'])

                for mod in key['mods']:
                    sleep(self.key_mod_delay)
                    directinput.ReleaseKey(mod)

            if repeat_delay:
                sleep(repeat_delay)
            else:
                sleep(self.key_repeat_delay)

    def get_collisions(self, key_name: str) -> list[str]:
        """ Get key name collisions (keys used for more than one binding).
        @param key_name: The key name (i.e. UI_Up, UI_Down).
        """
        key = self.keys.get(key_name)
        collisions = []
        for k, v in self.keys.items():
            if key == v:
                collisions.append(k)
        return collisions
