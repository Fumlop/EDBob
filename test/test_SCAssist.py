"""Standalone SC Assist test.

Requires Elite Dangerous running, in supercruise with a target selected.

Usage:
    ./venv/Scripts/python -m pytest test/test_SCAssist.py -s -k test_sc_assist_full
    ./venv/Scripts/python -m pytest test/test_SCAssist.py -s -k test_align_and_activate
    ./venv/Scripts/python -m pytest test/test_SCAssist.py -s -k test_activate_only
"""
import unittest
from time import sleep
from test.test_helpers import create_autopilot


class SCAssistTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ed_ap = create_autopilot()

    def _check_in_supercruise(self):
        from src.core.EDAP_data import FlagsSupercruise
        if not self.ed_ap.scr.elite_window_exists():
            self.skipTest("Elite Dangerous window not found")
        if not self.ed_ap.status.get_flag(FlagsSupercruise):
            self.skipTest("Not in supercruise")

    def test_activate_only(self):
        """Just activate SC Assist via nav panel (no alignment, no speed changes).
        Pre-align manually and set speed yourself before running.
        """
        self._check_in_supercruise()
        ap = self.ed_ap

        print("\n=== ACTIVATE SC ASSIST ONLY ===")
        print("  Opening nav panel and clicking SC Assist...")
        ap.nav_panel.activate_sc_assist()
        print("  Done. Check if 'MOVE THROTTLE TO BLUE ZONE' appeared.")

    def test_align_and_activate(self):
        """Align at 25%, throttle 0, activate SC Assist, throttle 75%.
        This is the production flow without the monitoring loop.
        """
        self._check_in_supercruise()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print("\n=== ALIGN + ACTIVATE SC ASSIST ===")

        # Align at 25%
        print("  Setting speed 25% for alignment...")
        ap.set_speed_25()
        sleep(1.0)

        print("  Compass aligning...")
        aligned = ap.compass_align(scr_reg)
        print(f"  Alignment result: {aligned}")

        if not aligned:
            print("  Retrying alignment...")
            sleep(2)
            aligned = ap.compass_align(scr_reg)
            print(f"  Retry result: {aligned}")
            if not aligned:
                print("  FAILED - could not align")
                return

        # Throttle 0
        print("  Throttle 0...")
        ap.set_speed_0()
        sleep(0.5)

        # Activate SC Assist
        print("  Activating SC Assist via Nav Panel...")
        ap.nav_panel.activate_sc_assist()
        sleep(1.0)

        # Throttle 75%
        print("  Throttle 75%...")
        ap.keys.send('SetSpeed75')
        print("  Done. SC Assist should be active now.")

    def test_sc_assist_full(self):
        """Full SC Assist flow: align, activate, and monitor until drop.
        This runs the actual production sc_assist method.
        """
        self._check_in_supercruise()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print("\n=== FULL SC ASSIST (production method) ===")
        print("  Running ap.sc_assist()...")
        ap.sc_assist(scr_reg, do_docking=False)
        print("  sc_assist() returned.")
        print(f"  Ship status: {ap.jn.ship_state()['status']}")


if __name__ == '__main__':
    unittest.main()
