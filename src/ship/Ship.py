"""Ship.py -- Ship identity, rates, config persistence.

The Ship is the "vehicle": it knows what it is, how fast it turns,
and how to load/save its configuration. The autopilot (ED_AP) is
the "controller" that decides where to go.
"""
from __future__ import annotations

import json
import os

from src.core.EDAP_data import ship_size_map, ship_rpy_sc_50
from src.core.EDlogger import logger


def _read_json(filepath: str) -> dict | None:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def _write_json(data: dict, filepath: str):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


SHIP_CONFIGS_PATH = './configs/ship_configs.json'


class Ship:
    """Represents the player's current ship: identity, turn rates, config."""

    # Rate at 0% throttle vs blue zone (50%) -- assumed ~60%
    ZERO_THROTTLE_RATE_FACTOR = 0.60

    def __init__(self, ap_ckb=None):
        self.ap_ckb = ap_ckb or (lambda *a: None)

        # Identity
        self.ship_type = None

        # Turn rates (deg/s)
        self.pitchrate = 33.0
        self.rollrate = 80.0
        self.yawrate = 8.0
        self.sunpitchuptime = 0.0

        # Factors (kept for config compat, currently unused in alignment)
        self.pitchfactor = 12.0
        self.rollfactor = 20.0
        self.yawfactor = 12.0

        # Throttle state
        self.speed_demand = None

        # Cargo hold
        self.cargo_capacity = 0
        self.cargo_current = 0

        # Config persistence
        self.ship_configs = {"Ship_Configs": {}}
        self.load_ship_configs()

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def update_ship_type(self, ship_type: str | None):
        """Set current ship type. Reloads config if ship changed.
        Returns True if ship actually changed.
        """
        if ship_type == self.ship_type:
            return False
        old = self.ship_type
        self.ship_type = ship_type
        if ship_type and ship_type in ship_size_map:
            self.load_ship_configuration(ship_type)
        return old is not None  # True = switched (not first load)

    # ------------------------------------------------------------------
    # Axis rates
    # ------------------------------------------------------------------

    def axis_max_rate(self, axis: str) -> float:
        """Return the known max rate (deg/s) for an axis.
        axis: 'pit', 'yaw', or 'roll'.
        """
        if axis == 'pit':
            return self.pitchrate
        elif axis == 'yaw':
            return self.yawrate
        return self.rollrate

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def load_ship_configs(self):
        """Read ship_configs.json from disk."""
        shp_cnf = _read_json(filepath=SHIP_CONFIGS_PATH)
        if shp_cnf is not None:
            if 'Ship_Configs' not in shp_cnf:
                shp_cnf['Ship_Configs'] = {}
            self.ship_configs = shp_cnf
            logger.debug("Ship: loaded ship_configs.json")
        else:
            _write_json(self.ship_configs, filepath=SHIP_CONFIGS_PATH)

    def load_ship_configuration(self, ship_type: str):
        """Load config for a ship with 3-tier priority:
        1. User's custom values from ship_configs.json
        2. Community defaults from ship_rpy_sc_50
        3. Hardcoded defaults
        """
        self.ap_ckb('log', f"Loading ship configuration for your {ship_type}")

        # Step 1: Hardcoded defaults
        self.rollrate = 80.0
        self.pitchrate = 33.0
        self.yawrate = 8.0
        self.sunpitchuptime = 0.0
        self.rollfactor = 20.0
        self.pitchfactor = 12.0
        self.yawfactor = 12.0
        logger.info(f"Loaded hardcoded default configuration for {ship_type}")

        # Step 2: Community defaults
        if ship_type in ship_rpy_sc_50:
            defaults = ship_rpy_sc_50[ship_type]
            self.rollrate = defaults.get('RollRate', 80.0)
            self.pitchrate = defaults.get('PitchRate', 33.0)
            self.yawrate = defaults.get('YawRate', 8.0)
            self.sunpitchuptime = defaults.get('SunPitchUp+Time', 0.0)
            logger.info(f"Loaded community defaults for {ship_type}")

        # Step 3: User's custom config
        if ship_type in self.ship_configs['Ship_Configs']:
            cfg = self.ship_configs['Ship_Configs'][ship_type]
            if any(k in cfg for k in ['RollRate', 'PitchRate', 'YawRate', 'SunPitchUp+Time']):
                self.rollrate = cfg.get('RollRate', self.rollrate)
                self.pitchrate = cfg.get('PitchRate', self.pitchrate)
                self.yawrate = cfg.get('YawRate', self.yawrate)
                self.sunpitchuptime = cfg.get('SunPitchUp+Time', self.sunpitchuptime)
                logger.info(f"Loaded custom config for {ship_type} from ship_configs.json")
            if any(k in cfg for k in ['RollFactor', 'PitchFactor', 'YawFactor']):
                self.rollfactor = cfg.get('RollFactor', self.rollfactor)
                self.pitchfactor = cfg.get('PitchFactor', self.pitchfactor)
                self.yawfactor = cfg.get('YawFactor', self.yawfactor)

    def save_ship_configs(self):
        """Save current rates to ship_configs.json for the current ship."""
        if not self.ship_type or self.ship_type not in ship_size_map:
            return
        if self.ship_type not in self.ship_configs['Ship_Configs']:
            self.ship_configs['Ship_Configs'][self.ship_type] = {}
            logger.debug(f"Created new ship config entry for: {self.ship_type}")

        cfg = self.ship_configs['Ship_Configs'][self.ship_type]
        cfg['PitchRate'] = self.pitchrate
        cfg['RollRate'] = self.rollrate
        cfg['YawRate'] = self.yawrate
        cfg['SunPitchUp+Time'] = self.sunpitchuptime
        cfg['PitchFactor'] = self.pitchfactor
        cfg['RollFactor'] = self.rollfactor
        cfg['YawFactor'] = self.yawfactor

        _write_json(self.ship_configs, filepath=SHIP_CONFIGS_PATH)
        logger.debug(f"Saved ship config for: {self.ship_type}")
