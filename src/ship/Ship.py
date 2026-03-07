"""Ship.py -- Ship identity, rates, steering, calibration, config persistence.

The Ship is the "vehicle": it knows what it is, how fast it turns,
how to steer, and how to load/save its configuration. The autopilot (ED_AP) is
the "controller" that decides where to go.
"""
from __future__ import annotations

import json
import math
import os
import time
from time import sleep

from src.core.EDAP_data import (
    ship_size_map, ship_rpy_sc_50,
    FlagsSupercruise, FlagsFsdJump,
)
from src.core.EDlogger import logger
from src.ed.EDJournal import (
    get_ship_size, check_fuel_scoop, check_adv_docking_computer,
    check_std_docking_computer, check_sco_fsd,
)


def _read_json(filepath: str) -> dict | None:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def _write_json(data: dict, filepath: str):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)


def _scale(inp: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Scale input from [in_min, in_max] to [out_min, out_max]."""
    return (inp - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


SHIP_CONFIGS_PATH = './configs/ship_configs.json'


class Ship:
    """Represents the player's current ship: identity, turn rates, steering, config."""

    # Rate estimation factors (relative to community SC 50% defaults)
    NORMAL_RATE_FACTOR = 2.0            # normal space ~2x SC 50%
    ZERO_THROTTLE_RATE_FACTOR = 0.60    # 0% throttle ~60% of 50% throttle

    # Axis configuration: maps axis name to rate attr, lookup key, threshold, and key bindings
    _AXIS_CONFIG = {
        'pitch': {'rate_attr': 'pitchrate', 'lookup_key': 'PitchRate',
                  'threshold': 30, 'pos_key': 'PitchUpButton', 'neg_key': 'PitchDownButton'},
        'roll':  {'rate_attr': 'rollrate',  'lookup_key': 'RollRate',
                  'threshold': 45, 'pos_key': 'RollRightButton', 'neg_key': 'RollLeftButton'},
        'yaw':   {'rate_attr': 'yawrate',   'lookup_key': 'YawRate',
                  'threshold': 30, 'pos_key': 'YawRightButton', 'neg_key': 'YawLeftButton'},
    }

    # Alignment constants
    MIN_HOLD_TIME = 0.50
    MAX_HOLD_TIME = 10.0
    ALIGN_CLOSE = 3.0           # degrees -- tightened with stable ring median
    ALIGN_SETTLE = 2.0          # seconds to let ship/compass settle after pitch/yaw
    ALIGN_TIMEOUT = 25.0        # seconds per axis
    AVG_DELAY = 0.01            # 10ms between compass reads
    ROLE_YAW_PITCH_CLOSE = 6.0  # roll and coarse alignment threshold
    ROLE_TRESHHOLD = 8.0        # only roll when yaw significantly off

    # Calibration: target degrees per axis (hold = target_deg / current_rate)
    CAL_SETTLE = 0.5
    CAL_TARGET_DEG = {'pitch': 45, 'pitch2': 60, 'roll': 120, 'yaw': 60}
    # Sequence: (key, axis, target_key) -- hold computed dynamically
    CAL_SEQUENCE = [
        # Round 1: yaw right, roll left, pitch down (ball stays up)
        ('YawRightButton',  'yaw',   'yaw'),
        ('RollLeftButton',  'roll',  'roll'),
        ('PitchDownButton', 'pitch', 'pitch'),
        # Round 2: yaw left, roll right, pitch up (reverses back)
        ('YawLeftButton',   'yaw',   'yaw'),
        ('RollRightButton', 'roll',  'roll'),
        ('PitchUpButton',   'pitch', 'pitch2'),
        # Round 3: pitch down, roll left, yaw right (ball stays up)
        ('PitchDownButton', 'pitch', 'pitch'),
        ('RollLeftButton',  'roll',  'roll'),
        ('YawRightButton',  'yaw',   'yaw'),
    ]
    _CAL_AXIS_KEY = {'pitch': 'pit', 'yaw': 'yaw', 'roll': 'roll'}

    # Throttle config
    _SPEED_CONFIG = {
        0:   {'demand': 'Speed0',   'sc_demand': 'SCSpeed0',   'key': 'SetSpeedZero'},
        25:  {'demand': 'Speed25',  'sc_demand': 'SCSpeed25',  'key': 'SetSpeed25',  'fallback': 50},
        50:  {'demand': 'Speed50',  'sc_demand': 'SCSpeed50',  'key': 'SetSpeed50'},
        100: {'demand': 'Speed100', 'sc_demand': 'SCSpeed100', 'key': 'SetSpeed100'},
    }

    def __init__(self, keys, status, ap_ckb=None):
        self.keys = keys              # EDKeys instance for sending inputs
        self.status = status          # StatusParser for flag checks
        self.ap_ckb = ap_ckb or (lambda *a: None)
        self.check_stop = lambda: None  # set by AP after creation

        # Identity
        self.ship_type = None

        # Turn rates (deg/s) -- active values reflect current flight mode
        self.pitchrate = 33.0
        self.rollrate = 80.0
        self.yawrate = 8.0
        self.sunpitchuptime = 0.0

        # Per-mode rate storage
        self._rates_normal = {'pitch': 33.0, 'roll': 80.0, 'yaw': 8.0}
        self._rates_sc = None  # None = no SC calibration, use normal rates
        self._flight_mode = 'normal'  # 'normal' or 'sc'

        # Factors (kept for config compat, currently unused in alignment)
        self.pitchfactor = 12.0
        self.rollfactor = 20.0
        self.yawfactor = 12.0

        # Throttle state
        self.speed_demand = None

        # Cargo hold
        self.cargo_capacity = 0
        self.cargo_current = 0

        # Module loadout (updated from journal Loadout events)
        self.ship_size = ''
        self.has_fuel_scoop = None
        self.has_adv_dock_comp = None
        self.has_std_dock_comp = None
        self.has_sco_fsd = None

        # Fuel state (updated from journal fuel events)
        self.fuel_level = None
        self.fuel_capacity = None
        self.fuel_percent = None
        self.is_scooping = False

        # Config persistence
        self.ship_configs = {"Ship_Configs": {}}
        self.load_ship_configs()

    # ------------------------------------------------------------------
    # Journal event integration
    # ------------------------------------------------------------------

    def register_journal_events(self, jn):
        """Register for journal events that affect ship properties."""
        jn.on_event('LoadGame', self._on_load_game)
        jn.on_event('Loadout', self._on_loadout)
        jn.on_event('_fuel_update', self._on_fuel_update)
        # Sync current state from journal's catchup
        self._sync_from_journal(jn.ship_state())

    def _sync_from_journal(self, s):
        """One-time sync of ship properties from journal state after catchup."""
        if s.get('type'):
            self.update_ship_type(s['type'])
            self.ship_size = s.get('ship_size', '')
        self.cargo_capacity = s.get('cargo_capacity') or 0
        self.has_fuel_scoop = s.get('has_fuel_scoop')
        self.has_adv_dock_comp = s.get('has_adv_dock_comp')
        self.has_std_dock_comp = s.get('has_std_dock_comp')
        self.has_sco_fsd = s.get('has_sco_fsd')
        self.fuel_level = s.get('fuel_level')
        self.fuel_capacity = s.get('fuel_capacity')
        self.fuel_percent = s.get('fuel_percent')
        self.is_scooping = s.get('is_scooping', False)

    def _on_load_game(self, log):
        """Handle LoadGame journal event."""
        self.update_ship_type(log['Ship'].lower())
        self.ship_size = get_ship_size(log['Ship'])

    def _on_loadout(self, log):
        """Handle Loadout journal event -- full ship state refresh."""
        self.update_ship_type(log['Ship'].lower())
        self.ship_size = get_ship_size(log['Ship'])
        self.cargo_capacity = log['CargoCapacity']
        self.has_fuel_scoop = check_fuel_scoop(log['Modules'])
        self.has_adv_dock_comp = check_adv_docking_computer(log['Modules'])
        self.has_std_dock_comp = check_std_docking_computer(log['Modules'])
        self.has_sco_fsd = check_sco_fsd(log['Modules'])

    def _on_fuel_update(self, log):
        """Handle any journal event carrying fuel data."""
        if 'FuelLevel' in log and self.ship_type != 'testbuggy':
            self.fuel_level = log['FuelLevel']
        if 'FuelCapacity' in log and self.ship_type != 'testbuggy':
            try:
                self.fuel_capacity = log['FuelCapacity']['Main']
            except (KeyError, TypeError):
                self.fuel_capacity = log['FuelCapacity']
        if log.get('event') == 'FuelScoop' and 'Total' in log:
            self.fuel_level = log['Total']
        self._update_fuel_percent()
        if log.get('event') == 'FuelScoop':
            self.is_scooping = self.fuel_percent is not None and self.fuel_percent < 100
        else:
            self.is_scooping = False

    def _update_fuel_percent(self):
        """Recalculate fuel percentage from level and capacity."""
        if self.fuel_level and self.fuel_capacity:
            self.fuel_percent = round((self.fuel_level / self.fuel_capacity) * 100)
        else:
            self.fuel_percent = 10

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def update_ship_type(self, ship_type: str | None):
        """Set current ship type. Reloads config if ship changed.
        Returns True if ship actually changed.
        """
        if ship_type == self.ship_type:
            self.update_flight_mode()  # rates may need switching even if ship didn't change
            return False
        old = self.ship_type
        self.ship_type = ship_type
        if ship_type and ship_type in ship_size_map:
            self.load_ship_configuration(ship_type)  # calls _apply_mode_rates() internally
        return old is not None  # True = switched (not first load)

    # ------------------------------------------------------------------
    # Axis rates
    # ------------------------------------------------------------------

    def update_flight_mode(self):
        """Check status flags and switch active rates if flight mode changed."""
        in_sc = self.status.get_flag(FlagsSupercruise)
        new_mode = 'sc' if in_sc else 'normal'
        if new_mode != self._flight_mode:
            self._flight_mode = new_mode
            self._apply_mode_rates()

    def _apply_mode_rates(self):
        """Set pitchrate/rollrate/yawrate from the current flight mode's rate set."""
        if self._flight_mode == 'sc' and self._rates_sc is not None:
            rates = self._rates_sc
        else:
            rates = self._rates_normal
        self.pitchrate = rates['pitch']
        self.rollrate = rates['roll']
        self.yawrate = rates['yaw']
        logger.info(f"Flight mode -> {self._flight_mode}: pitch={self.pitchrate} roll={self.rollrate} yaw={self.yawrate}")

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
    # Throttle
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Steering
    # ------------------------------------------------------------------

    @staticmethod
    def _roll_on_centerline(roll_deg, close):
        """Check if the dot is on the vertical centerline (near 0 or +/-180 degrees)."""
        return abs(roll_deg) < close or (180 - abs(roll_deg)) < close

    def _get_dist(self, axis, off):
        """Get distance to target for an axis (ceiled to full degrees)."""
        if axis == 'roll':
            return math.ceil(min(abs(off['roll']), 180 - abs(off['roll'])))
        return math.ceil(abs(off[axis]))

    def _is_aligned(self, axis, off, close):
        """Check if aligned on an axis."""
        if axis == 'roll':
            return self._roll_on_centerline(off['roll'], close)
        return abs(off[axis]) < close

    def _axis_pick_key(self, axis, deg):
        """Pick the correct key for moving an axis toward center."""
        if axis == 'roll':
            return 'RollRightButton' if deg > 0 else 'RollLeftButton'
        elif axis == 'pit':
            if abs(deg) <= 90:
                return 'PitchUpButton' if deg > 0 else 'PitchDownButton'
            else:
                return 'PitchDownButton' if deg > 0 else 'PitchUpButton'
        else:
            return 'YawRightButton' if deg > 0 else 'YawLeftButton'

    def align_axis(self, scr_reg, axis, off, close=10.0, timeout=None, *, get_offset_fn):
        """Align one axis using configured rate and calculated holds.
        @param get_offset_fn: callable(scr_reg) -> offset dict or None
        @return: Updated offset dict, or None if compass lost.
        """
        if timeout is None:
            timeout = self.ALIGN_TIMEOUT
        if off.get('z', 1) < 0:
            return off
        if self._is_aligned(axis, off, close):
            return off

        start = time.time()
        remaining = self._get_dist(axis, off)
        rate = self.axis_max_rate(axis)
        key = self._axis_pick_key(axis, off[axis])

        logger.info(f"Align {axis}: {off[axis]:.1f}deg, dist={remaining:.1f}, rate={rate:.1f}, key={key}")

        while remaining > close and (time.time() - start) < timeout:
            self.check_stop()
            factor = 1.0 if remaining > 10.0 else 0.95
            hold_time = (remaining * factor) / rate
            hold_time = max(self.MIN_HOLD_TIME, min(self.MAX_HOLD_TIME, hold_time))

            logger.debug(f"Align {axis}: remaining={remaining:.1f}deg, hold={hold_time:.2f}s, rate={rate:.1f}, key={key}")
            self.keys.send(key, hold=hold_time)
            sleep(self.ALIGN_SETTLE)

            if self.status.get_flag(FlagsFsdJump):
                logger.info(f"Align {axis}: FSD jumped during align, aborting")
                return off

            new_off = get_offset_fn(scr_reg)
            if new_off is None:
                sleep(0.5)
                new_off = get_offset_fn(scr_reg)
                if new_off is None:
                    return off

            if new_off.get('z', 1) < 0:
                logger.info(f"Align {axis}: target went behind, aborting axis align")
                return new_off

            if self._is_aligned(axis, new_off, close):
                logger.info(f"Align {axis}: aligned at {new_off[axis]:.1f}deg ({time.time()-start:.1f}s)")
                return new_off

            new_dist = self._get_dist(axis, new_off)
            old_key = key
            key = self._axis_pick_key(axis, new_off[axis])
            if key != old_key:
                logger.debug(f"Align {axis}: direction changed {remaining:.1f}->{new_dist:.1f}, key={key}")

            remaining = new_dist
            off = new_off

        if (time.time() - start) >= timeout:
            logger.warning(f"Align {axis}: timeout after {timeout}s")
        return off

    def roll_to_centerline(self, scr_reg, off, close=10.0, *, get_offset_fn):
        """Coarse roll to vertical centerline."""
        return self.align_axis(scr_reg, 'roll', off, close, get_offset_fn=get_offset_fn)

    def yaw_to_center(self, scr_reg, off, close=10.0, *, get_offset_fn):
        """Yaw to horizontal center."""
        return self.align_axis(scr_reg, 'yaw', off, close, get_offset_fn=get_offset_fn)

    def pitch_to_center(self, scr_reg, off, close=10.0, *, get_offset_fn):
        """Pitch to vertical center."""
        return self.align_axis(scr_reg, 'pit', off, close, get_offset_fn=get_offset_fn)

    def avg_offset(self, scr_reg, get_offset_fn):
        """Take 3 reads with 10ms gaps, return average pit/yaw/roll.
        @return: dict with avg 'pit','yaw','roll' or None if any read fails.
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
            'roll': sum(r['roll'] for r in reads) / 3,
        }

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
            ship_cfg = self.ship_configs['Ship_Configs'][self.ship_type]
            if self.speed_demand not in ship_cfg:
                ship_cfg[self.speed_demand] = dict()
            speed_cfg = ship_cfg[self.speed_demand]
            if cfg['lookup_key'] not in speed_cfg:
                speed_cfg[cfg['lookup_key']] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_cfg[cfg['lookup_key']].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    ratio_val = _scale(abs_deg, last_deg, key_deg, last_val, value)
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

    def send_pitch(self, deg):
        """Pitch by deg degrees (positive=up, negative=down). Uses current mode rate."""
        key = 'PitchUpButton' if deg > 0 else 'PitchDownButton'
        self.keys.send(key, hold=abs(deg) / self.pitchrate)

    def send_roll(self, deg):
        """Roll by deg degrees (positive=right, negative=left). Uses current mode rate."""
        key = 'RollRightButton' if deg > 0 else 'RollLeftButton'
        self.keys.send(key, hold=abs(deg) / self.rollrate)

    def hold_time(self, axis, deg):
        """Calculate hold time for a given axis and angle. For timeouts etc."""
        rate = self.axis_max_rate(axis)
        return abs(deg) / rate

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate_rates(self, mode, scr_reg, get_offset_fn):
        """Run the calibration sequence measuring pitch/roll/yaw rates.
        @param mode: 'normal' for normal space, 'sc_zero' for SC at 0% throttle.
        @param scr_reg: Screen_Regions instance for compass reads.
        @param get_offset_fn: callable(scr_reg) -> offset dict or None.
        """
        mode_label = 'Normal Space' if mode == 'normal' else 'Supercruise (0%)'
        self.ap_ckb('log', f'Starting {mode_label} calibration...')
        self.ap_ckb('log', 'Center target on compass, then hold still.')
        sleep(1)

        total = len(self.CAL_SEQUENCE)
        samples = {'pitch': [], 'roll': [], 'yaw': []}

        for step, (key, axis, target_key) in enumerate(self.CAL_SEQUENCE, 1):
            self.check_stop()

            rate = self.axis_max_rate(axis)
            hold = min(self.CAL_TARGET_DEG[target_key] / rate, 3.0)
            axis_key = self._CAL_AXIS_KEY[axis]

            before = self.avg_offset(scr_reg, get_offset_fn)
            if before is None:
                self.ap_ckb('log', f'Step {step}/{total}: compass read failed (before), skipping')
                self.keys.send(key, hold=hold)
                sleep(self.CAL_SETTLE)
                continue

            self.keys.send(key, hold=hold)
            sleep(self.CAL_SETTLE)

            after = self.avg_offset(scr_reg, get_offset_fn)
            if after is None:
                self.ap_ckb('log', f'Step {step}/{total}: compass read failed (after), skipping')
                continue

            delta = abs(after[axis_key] - before[axis_key])
            measured_rate = delta / hold
            samples[axis].append(measured_rate)
            self.ap_ckb('log', f'Step {step}/{total}: {axis} = {measured_rate:.1f} deg/s (delta {delta:.1f}, hold {hold:.2f}s)')

        # Calculate averages
        rates = {}
        for axis in ('pitch', 'roll', 'yaw'):
            if samples[axis]:
                avg = sum(samples[axis]) / len(samples[axis])
                rates[axis] = round(avg, 1)
                self.ap_ckb('log', f'{axis.capitalize()} rate: {avg:.1f} deg/s ({len(samples[axis])} samples)')
            else:
                self.ap_ckb('log', f'{axis.capitalize()}: no valid samples!')

        if not rates:
            self.ap_ckb('log', 'Calibration failed -- no valid measurements')
            return

        # Save to ship_configs.json
        mode_key = 'Normalspace' if mode == 'normal' else 'Supercruise-zero'
        ship = self.ship_type
        if ship and ship in ship_size_map:
            if ship not in self.ship_configs['Ship_Configs']:
                self.ship_configs['Ship_Configs'][ship] = {}
            cfg = self.ship_configs['Ship_Configs'][ship]

            cfg[mode_key] = {
                'PitchRate': rates.get('pitch', 0),
                'RollRate': rates.get('roll', 0),
                'YawRate': rates.get('yaw', 0),
            }

            # Also update top-level rates for backward compat
            if 'pitch' in rates:
                cfg['PitchRate'] = rates['pitch']
            if 'roll' in rates:
                cfg['RollRate'] = rates['roll']
            if 'yaw' in rates:
                cfg['YawRate'] = rates['yaw']

            # Store into the correct per-mode rate set
            rate_dict = {
                'pitch': rates.get('pitch', self.pitchrate),
                'roll': rates.get('roll', self.rollrate),
                'yaw': rates.get('yaw', self.yawrate),
            }
            if mode == 'normal':
                self._rates_normal = rate_dict
            else:
                self._rates_sc = rate_dict
            self._apply_mode_rates()

            _write_json(self.ship_configs, filepath=SHIP_CONFIGS_PATH)
            self.ap_ckb('log', f'Saved {mode_label} rates for {ship}')
            self.ap_ckb('update_ship_cfg')
        else:
            self.ap_ckb('log', 'Cannot save -- no ship detected')

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

        # Derive operating rates from community defaults (SC rates at 50% throttle)
        # Normal space: 2x SC50, at 0% throttle: * 0.6
        # SC at 0% throttle: SC50 * 0.6
        nf = self.NORMAL_RATE_FACTOR * self.ZERO_THROTTLE_RATE_FACTOR   # 2.0 * 0.6 = 1.2
        sf = self.ZERO_THROTTLE_RATE_FACTOR                             # 0.6
        self._rates_normal = {'pitch': self.pitchrate * nf, 'roll': self.rollrate * nf, 'yaw': self.yawrate * nf}
        self._rates_sc = {'pitch': self.pitchrate * sf, 'roll': self.rollrate * sf, 'yaw': self.yawrate * sf}

        # Load per-mode overrides from calibration sub-dicts
        if ship_type in self.ship_configs['Ship_Configs']:
            cfg = self.ship_configs['Ship_Configs'][ship_type]
            if 'Normalspace' in cfg:
                ns = cfg['Normalspace']
                self._rates_normal = {
                    'pitch': ns.get('PitchRate', self._rates_normal['pitch']),
                    'roll':  ns.get('RollRate',  self._rates_normal['roll']),
                    'yaw':   ns.get('YawRate',   self._rates_normal['yaw']),
                }
                logger.info(f"Loaded Normalspace calibration for {ship_type}")
            if 'Supercruise-zero' in cfg:
                sc = cfg['Supercruise-zero']
                self._rates_sc = {
                    'pitch': sc.get('PitchRate', self._rates_normal['pitch']),
                    'roll':  sc.get('RollRate',  self._rates_normal['roll']),
                    'yaw':   sc.get('YawRate',   self._rates_normal['yaw']),
                }
                logger.info(f"Loaded Supercruise-zero calibration for {ship_type}")

        # Apply correct rates for current flight mode
        self._apply_mode_rates()

    def save_ship_configs(self):
        """Save ship_configs.json to disk. Rates are stored only via calibration
        sub-dicts (Normalspace/Supercruise-zero), not as top-level values."""
        if not self.ship_type or self.ship_type not in ship_size_map:
            return
        if self.ship_type not in self.ship_configs['Ship_Configs']:
            self.ship_configs['Ship_Configs'][self.ship_type] = {}
            logger.debug(f"Created new ship config entry for: {self.ship_type}")

        _write_json(self.ship_configs, filepath=SHIP_CONFIGS_PATH)
        logger.debug(f"Saved ship config for: {self.ship_type}")
