"""Standalone navball alignment test.

Requires Elite Dangerous running, in supercruise with a target selected.

Usage:
    ./venv/Scripts/python -m pytest test/test_NavballAlign.py -s -k test_align_only
    ./venv/Scripts/python -m pytest test/test_NavballAlign.py -s -k test_read_offsets
    ./venv/Scripts/python -m pytest test/test_NavballAlign.py -s -k test_compass_front
    ./venv/Scripts/python -m pytest test/test_NavballAlign.py -s -k test_compass_behind
"""
import unittest
from time import sleep
from test.test_helpers import create_autopilot


def log_offsets(label, nav_off, tar_off):
    """Log all compass + target offset fields."""
    print(f"\n=== {label} ===")
    if nav_off:
        print(f"  NAV: pit={nav_off['pit']:+7.2f}  roll={nav_off['roll']:+7.1f}  "
              f"yaw={nav_off['yaw']:+7.2f}  x={nav_off['x']:+.4f}  y={nav_off['y']:+.4f}  z={nav_off['z']:+.1f}")
    else:
        print(f"  NAV: ---")
    if tar_off:
        print(f"  TAR: pit={tar_off['pit']:+7.2f}  roll={tar_off['roll']:+7.1f}  "
              f"yaw={tar_off['yaw']:+7.2f}  occ={'YES' if tar_off.get('occ') else 'no'}")
    else:
        print(f"  TAR: ---")


class NavballAlignTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ed_ap = create_autopilot()

    def _check_elite_running(self):
        from src.core.EDAP_data import FlagsSupercruise
        if not self.ed_ap.scr.elite_window_exists():
            self.skipTest("Elite Dangerous window not found")
        if not self.ed_ap.status.get_flag(FlagsSupercruise):
            self.skipTest("Not in supercruise")

    def test_align_only(self):
        """Run production sc_target_align directly (no scramble)."""
        self._check_elite_running()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        nav_off = ap.get_nav_offset(scr_reg)
        tar_off = ap.get_target_offset(scr_reg)
        log_offsets("BEFORE ALIGNMENT", nav_off, tar_off)

        from src.autopilot.ED_AP import ScTargetAlignReturn
        print("\n=== ALIGNMENT (mirrors mnvr_to_target) ===")
        # Speed set manually by user before running test
        sleep(0.5)

        for attempt in range(5):
            result = ap.sc_target_align(scr_reg)
            print(f"  Attempt {attempt+1}: {result}")
            if result == ScTargetAlignReturn.Found:
                break
            elif result == ScTargetAlignReturn.Disengage:
                break
            sleep(1.0)
            sleep(1.0)

        nav_off = ap.get_nav_offset(scr_reg)
        tar_off = ap.get_target_offset(scr_reg)
        log_offsets("AFTER ALIGNMENT", nav_off, tar_off)

    def test_read_offsets(self):
        """Just read and log compass + target offsets 10 times, no movement."""
        self._check_elite_running()
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print(f"\n=== OFFSET READINGS (10x) ===")
        print(f"  {'#':>4}  {'pit':>7} {'roll':>7} {'yaw':>7} {'x':>7} {'y':>7} {'z':>4}  |  "
              f"{'pit':>7} {'roll':>7} {'yaw':>7} {'occ':>4}")
        for i in range(10):
            nav_off = ap.get_nav_offset(scr_reg)
            tar_off = ap.get_target_offset(scr_reg)

            nav_str = "   ---"
            if nav_off:
                nav_str = (f"{nav_off['pit']:+7.2f} {nav_off['roll']:+7.1f} {nav_off['yaw']:+7.2f} "
                           f"{nav_off['x']:+7.4f} {nav_off['y']:+7.4f} {nav_off['z']:+4.1f}")

            tar_str = "   ---"
            if tar_off:
                tar_str = (f"{tar_off['pit']:+7.2f} {tar_off['roll']:+7.1f} {tar_off['yaw']:+7.2f} "
                           f"{'OCC' if tar_off.get('occ') else ' ok':>4}")

            print(f"  [{i+1:2d}]  {nav_str}  |  {tar_str}")
            sleep(0.5)

    def _compass_debug_loop(self, label, count=10, delay=3.0):
        """Shared compass debug capture loop."""
        import cv2
        ap = self.ed_ap
        scr_reg = ap.scrReg

        print(f"\n=== COMPASS DEBUG: {label} ({count}x, {delay}s apart) ===")
        print(f"  Move dot border-to-border while {label}...")
        for i in range(count):
            # Capture compass region
            full_img = scr_reg.capture_region(ap.scr, 'compass', inv_col=False)
            full_bgr = cv2.cvtColor(full_img, cv2.COLOR_BGRA2BGR) if full_img.shape[2] == 4 else full_img

            # Run ML to find compass quad
            ml_res = ap.mach_learn.predict(full_bgr)
            if not ml_res or len(ml_res) != 1:
                print(f"  [{i+1}] ML: no compass found")
                sleep(1.0)
                continue

            quad = ml_res[0].bounding_quad
            from src.screen.Screen import crop_image_pix
            compass_img = crop_image_pix(full_img, quad)
            comp_h, comp_w = compass_img.shape[:2]

            compass_bgr = cv2.cvtColor(compass_img, cv2.COLOR_BGRA2BGR) if compass_img.shape[2] == 4 else compass_img
            compass_hsv = cv2.cvtColor(compass_bgr, cv2.COLOR_BGR2HSV)

            # Same masks as production
            orange_mask = cv2.inRange(compass_hsv, (5, 100, 100), (25, 255, 255))
            front_mask = cv2.inRange(compass_hsv, (75, 40, 170), (105, 255, 255))
            front_mask = cv2.bitwise_and(front_mask, cv2.bitwise_not(orange_mask))
            dark_mask = cv2.inRange(compass_hsv, (0, 0, 0), (180, 255, 50))
            dark_mask = cv2.bitwise_and(dark_mask, cv2.bitwise_not(orange_mask))

            front_contours, _ = cv2.findContours(front_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            dark_contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            front_valid = [c for c in front_contours if 5 < cv2.contourArea(c) < comp_w * comp_h * 0.3]
            dark_valid = [c for c in dark_contours if 5 < cv2.contourArea(c) < comp_w * comp_h * 0.3]

            front_areas = sorted([cv2.contourArea(c) for c in front_valid], reverse=True)[:3]
            dark_areas = sorted([cv2.contourArea(c) for c in dark_valid], reverse=True)[:3]

            # Sample center pixel HSV
            cy, cx = comp_h // 2, comp_w // 2
            center_hsv = compass_hsv[cy, cx]

            print(f"  [{i+1}] size={comp_w}x{comp_h}  center_hsv={center_hsv}")
            print(f"        front: {len(front_valid)} contours, areas={front_areas}")
            print(f"        dark:  {len(dark_valid)} contours, areas={dark_areas}")
            print(f"        orange: {cv2.countNonZero(orange_mask)} px")

            # If front found, show its center HSV
            if front_valid:
                largest = max(front_valid, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    dx, dy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                    print(f"        front dot @ ({dx},{dy}) hsv={compass_hsv[dy, dx]}")
            if dark_valid:
                largest = max(dark_valid, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    dx, dy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                    print(f"        dark dot  @ ({dx},{dy}) hsv={compass_hsv[dy, dx]}")

            # Save compass crop for manual inspection
            cv2.imwrite(f'compass_debug_{label}_{i+1}.png', compass_bgr)

            sleep(delay)

    def test_compass_front(self):
        """Debug compass detection with target IN FRONT. Move dot border-to-border."""
        self._check_elite_running()
        self._compass_debug_loop("front")

    def test_compass_behind(self):
        """Debug compass detection with target BEHIND. Move dot border-to-border."""
        self._check_elite_running()
        self._compass_debug_loop("behind")


if __name__ == '__main__':
    unittest.main()
