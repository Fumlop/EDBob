"""Standalone waypoint file loading test.

Does NOT require Elite Dangerous to be running.
Validates waypoint JSON structure and data.

Usage:
    ./venv/Scripts/python -m pytest test/test_WaypointLoading.py -s
"""
import os
import unittest


def dummy_cb(msg, body=None):
    if body:
        print(f"[CB] {msg}: {body}")
    else:
        print(f"[CB] {msg}")


class WaypointLoadingTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src.autopilot.ED_AP import EDAutopilot
        cls.ed_ap = EDAutopilot(cb=dummy_cb)

    def test_load_default_waypoints(self):
        """Load the default waypoints.json."""
        from src.autopilot.EDWayPoint import EDWayPoint
        wp = EDWayPoint(self.ed_ap)
        res = wp.load_waypoint_file('./waypoints/waypoints.json')
        print(f"\n  Load result: {res}")
        if res:
            print(f"  Waypoints loaded: {len(wp.waypoints)}")
            for key in wp.waypoints:
                wpt = wp.waypoints[key]
                sys_name = wpt.get('SystemName', '?')
                stn_name = wpt.get('StationName', '?')
                completed = wpt.get('Completed', False)
                skip = wpt.get('Skip', False)
                print(f"    [{key}] {sys_name} / {stn_name} "
                      f"{'[DONE]' if completed else ''}"
                      f"{'[SKIP]' if skip else ''}")
        self.assertTrue(res, "Failed to load waypoints.json")

    def test_load_all_waypoint_files(self):
        """Load all .json files in waypoints/ folder."""
        from src.autopilot.EDWayPoint import EDWayPoint

        wp_dir = './waypoints/'
        files = [f for f in os.listdir(wp_dir) if f.endswith('.json')]
        print(f"\n  Found {len(files)} waypoint files")

        for fname in files:
            wp = EDWayPoint(self.ed_ap)
            path = os.path.join(wp_dir, fname)
            res = wp.load_waypoint_file(path)
            count = len(wp.waypoints) if res else 0
            print(f"    {fname:<30} loaded={res}, waypoints={count}")

        self.assertGreater(len(files), 0, "No waypoint files found")

    def test_get_next_waypoint(self):
        """Get the next incomplete waypoint."""
        from src.autopilot.EDWayPoint import EDWayPoint
        wp = EDWayPoint(self.ed_ap)
        res = wp.load_waypoint_file('./waypoints/waypoints.json')
        if not res:
            self.skipTest("Could not load waypoints.json")

        dest_key, dest = wp.get_waypoint()
        if dest_key:
            print(f"\n  Next waypoint: [{dest_key}]")
            print(f"    System: {dest.get('SystemName', '?')}")
            print(f"    Station: {dest.get('StationName', '?')}")
            buy = dest.get('BuyCommodities', {})
            sell = dest.get('SellCommodities', {})
            if buy:
                print(f"    Buy: {buy}")
            if sell:
                print(f"    Sell: {sell}")
        else:
            print("\n  All waypoints completed (or empty)")

    def test_waypoint_structure(self):
        """Validate required fields in each waypoint."""
        from src.autopilot.EDWayPoint import EDWayPoint
        wp = EDWayPoint(self.ed_ap)
        res = wp.load_waypoint_file('./waypoints/waypoints.json')
        if not res:
            self.skipTest("Could not load waypoints.json")

        required_fields = ['SystemName', 'StationName', 'BuyCommodities', 'SellCommodities']
        print()
        errors = []
        for key in wp.waypoints:
            wpt = wp.waypoints[key]
            for field in required_fields:
                if field not in wpt:
                    errors.append(f"  [{key}] missing '{field}'")

        if errors:
            for e in errors:
                print(e)
        else:
            print(f"  All {len(wp.waypoints)} waypoints have required fields")

        self.assertEqual(len(errors), 0, f"Waypoint structure errors:\n" + "\n".join(errors))


if __name__ == '__main__':
    unittest.main()
