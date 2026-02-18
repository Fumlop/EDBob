"""Standalone sun avoidance test.

Requires Elite Dangerous running, in supercruise.

Usage:
    ./venv/Scripts/python -m pytest test/test_SunAvoidance.py -s -k test_sun_detect
    ./venv/Scripts/python -m pytest test/test_SunAvoidance.py -s -k test_sun_avoid
"""
import unittest
from time import sleep
from test.test_helpers import create_autopilot


class SunAvoidanceTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ed_ap = create_autopilot()

    def _check_in_space(self):
        if not self.ed_ap.scr.elite_window_exists():
            self.skipTest("Elite Dangerous window not found")

    def test_sun_detect(self):
        """Read sun brightness percentage 10 times, 1s apart."""
        self._check_in_space()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print(f"\n=== SUN DETECTION (10 reads) ===")
        for i in range(10):
            pct = scr_reg.sun_percent(scr_reg.screen)
            dead_ahead = ap.is_sun_dead_ahead(scr_reg)
            print(f"  [{i+1:2d}] Sun brightness: {pct:.1f}%  dead_ahead={dead_ahead}")
            sleep(1.0)

    def test_sun_avoid(self):
        """Run sun avoidance -- will pitch up if sun is ahead.
        Point your ship at the sun before running this test.
        """
        self._check_in_space()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print(f"\n=== SUN AVOIDANCE ===")
        pct_before = scr_reg.sun_percent(scr_reg.screen)
        print(f"  Before: sun={pct_before:.1f}%")

        if pct_before <= 5:
            print("  Sun not ahead (<=5%), skipping avoidance maneuver")
            print("  Point ship at star and re-run to test avoidance")
            return

        ap.keys.send('SetSpeed75')
        sleep(0.5)
        ap.sun_avoid(scr_reg)

        pct_after = scr_reg.sun_percent(scr_reg.screen)
        print(f"  After:  sun={pct_after:.1f}%")
        self.assertLess(pct_after, pct_before, "Sun brightness should decrease after avoidance")


if __name__ == '__main__':
    unittest.main()
