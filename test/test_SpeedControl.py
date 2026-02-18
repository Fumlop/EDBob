"""Standalone speed control test.

Requires Elite Dangerous running (any flight mode).

Usage:
    ./venv/Scripts/python -m pytest test/test_SpeedControl.py -s
"""
import unittest
from time import sleep
from test.test_helpers import create_autopilot


class SpeedControlTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ed_ap = create_autopilot()

    def _check_running(self):
        if not self.ed_ap.scr.elite_window_exists():
            self.skipTest("Elite Dangerous window not found")

    def test_throttle_cycle(self):
        """Cycle through 0 -> 50 -> 100 -> 0 with delays."""
        self._check_running()
        ap = self.ed_ap

        print(f"\n=== THROTTLE CYCLE ===")

        print("  Setting speed 0...")
        ap.set_speed_0()
        sleep(2.0)

        print("  Setting speed 50% (Key_Y)...")
        ap.set_speed_50()
        sleep(3.0)

        print("  Setting speed 0...")
        ap.set_speed_0()
        sleep(2.0)

        print("  Setting speed 75% (raw key send)...")
        ap.keys.send('SetSpeed75')
        sleep(3.0)

        print("  Setting speed 100...")
        ap.set_speed_100()
        sleep(2.0)

        print("  Setting speed 0...")
        ap.set_speed_0()
        sleep(1.0)
        print("  Cycle complete")

    def test_key_sends(self):
        """Dump actual key bindings with scancodes."""
        self._check_running()
        ap = self.ed_ap

        throttle_keys = ['SetSpeedZero', 'SetSpeed50', 'SetSpeed75', 'SetSpeed100', 'SetSpeed25']

        print(f"\n=== KEY BINDING DETAIL ===")
        for name in throttle_keys:
            key_data = ap.keys.keys.get(name)
            if key_data:
                key_name = ap.keys.reversed_dict.get(key_data['key'], '???')
                print(f"  {name:<20}: scancode={key_data['key']:#06x}  key={key_name}  mods={key_data['mods']}"
                      f"{'  HOLD' if key_data.get('hold') else ''}")
            else:
                print(f"  {name:<20}: NOT BOUND")


if __name__ == '__main__':
    unittest.main()
