"""Standalone journal parsing test.

Does NOT require Elite Dangerous to be running.
Tests journal file discovery, ship state parsing, and module detection.

Usage:
    python -m pytest test/test_JournalParsing.py -s
"""
import unittest
from src.ed.EDJournal import EDJournal, check_fuel_scoop, check_adv_docking_computer, \
    check_std_docking_computer, check_sco_fsd


def dummy_cb(msg, body=None):
    if body:
        print(f"[CB] {msg}: {body}")
    else:
        print(f"[CB] {msg}")


class JournalParsingTestCase(unittest.TestCase):

    def test_find_latest_journal(self):
        """Find the most recent journal file."""
        jn = EDJournal(cb=dummy_cb)
        latest = jn.get_latest_log()
        print(f"\n  Latest journal: {latest}")
        self.assertIsNotNone(latest, "No journal file found")
        self.assertTrue(latest.endswith('.log'), "Journal file should be .log")

    def test_ship_state(self):
        """Parse ship state from journal -- modules, cargo capacity, ship type."""
        jn = EDJournal(cb=dummy_cb)
        state = jn.ship_state()
        print(f"\n  Ship state keys: {list(state.keys())}")

        # Log interesting fields
        for key in ['ship_type', 'cargo_capacity', 'fuel_capacity', 'cur_system', 'cur_station']:
            val = state.get(key, 'N/A')
            print(f"  {key}: {val}")

        self.assertIsNotNone(state, "ship_state() returned None")

    def test_module_detection(self):
        """Check module detection -- fuel scoop, docking computer, SCO FSD."""
        jn = EDJournal(cb=dummy_cb)
        state = jn.ship_state()
        modules = state.get('modules', None)

        print(f"\n  Modules found: {len(modules) if modules else 0}")

        has_scoop = check_fuel_scoop(modules)
        has_adv_dock = check_adv_docking_computer(modules)
        has_std_dock = check_std_docking_computer(modules)
        has_sco = check_sco_fsd(modules)

        print(f"  Fuel scoop: {has_scoop}")
        print(f"  Adv docking computer: {has_adv_dock}")
        print(f"  Std docking computer: {has_std_dock}")
        print(f"  SCO FSD: {has_sco}")

        # At least one should be detectable (or not, but no crash)
        self.assertIsInstance(has_scoop, bool)
        self.assertIsInstance(has_adv_dock, bool)

    def test_ship_dict_fields(self):
        """Verify ship dict has expected fields populated."""
        jn = EDJournal(cb=dummy_cb)
        state = jn.ship_state()

        expected_fields = ['ship_type', 'cargo_capacity', 'fuel_capacity', 'modules']
        print(f"\n  Checking fields: {expected_fields}")
        for field in expected_fields:
            val = state.get(field)
            print(f"  {field}: {val if not isinstance(val, list) else f'[{len(val)} items]'}")
            self.assertIn(field, state, f"Missing field: {field}")


if __name__ == '__main__':
    unittest.main()
