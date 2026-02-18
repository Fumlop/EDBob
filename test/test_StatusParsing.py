"""Standalone status parsing test.

Does NOT require Elite Dangerous to be running (reads Status.json from disk).
Tests flag decoding, pips, GUI focus, and cleaned data.

Usage:
    python -m pytest test/test_StatusParsing.py -s
"""
import unittest
from src.ed.StatusParser import StatusParser
from src.core.EDAP_data import (FlagsDocked, FlagsLanded, FlagsSupercruise,
                                 FlagsInMainShip, FlagsFsdCharging, FlagsFsdJump,
                                 FlagsShieldsUp, FlagsLowFuel, FlagsOverHeating)


class StatusParsingTestCase(unittest.TestCase):

    def test_read_status(self):
        """Read and display current status data."""
        sp = StatusParser()
        data = sp.get_cleaned_data()
        print(f"\n  Status timestamp: {data.get('timestamp', 'N/A')}")
        print(f"  Raw Flags: {data.get('Flags', 'N/A')}")
        print(f"  Raw Flags2: {data.get('Flags2', 'N/A')}")
        print(f"  Cargo: {data.get('Cargo', 'N/A')}")
        print(f"  GUI Focus: {data.get('GuiFocus', 'N/A')}")
        self.assertIsNotNone(data, "Status data is None")

    def test_translate_flags(self):
        """Decode flags integer to readable state names."""
        sp = StatusParser()
        data = sp.get_cleaned_data()
        flags = data.get('Flags', 0)
        flags2 = data.get('Flags2', 0)

        true_flags = sp.translate_flags(flags)
        true_flags2 = sp.translate_flags2(flags2)

        print(f"\n  Active Flags:  {true_flags}")
        print(f"  Active Flags2: {true_flags2}")

        self.assertIsInstance(true_flags, dict)
        self.assertIsInstance(true_flags2, dict)

    def test_individual_flags(self):
        """Check individual flag values."""
        sp = StatusParser()

        flags_to_check = {
            'Docked': FlagsDocked,
            'Landed': FlagsLanded,
            'Supercruise': FlagsSupercruise,
            'InMainShip': FlagsInMainShip,
            'FsdCharging': FlagsFsdCharging,
            'FsdJump': FlagsFsdJump,
            'ShieldsUp': FlagsShieldsUp,
            'LowFuel': FlagsLowFuel,
            'OverHeating': FlagsOverHeating,
        }

        print()
        for name, flag in flags_to_check.items():
            val = sp.get_flag(flag)
            print(f"  {name:<20}: {val}")
            self.assertIsInstance(val, bool)

    def test_pips(self):
        """Read and display pip distribution."""
        sp = StatusParser()
        data = sp.get_cleaned_data()
        pips_raw = data.get('Pips', [0, 0, 0])
        pips = sp.transform_pips(pips_raw)
        print(f"\n  Pips raw: {pips_raw}")
        print(f"  Pips: SYS={pips['system']} ENG={pips['engines']} WEP={pips['weapons']}")
        self.assertEqual(len(pips), 3)

    def test_gui_focus(self):
        """Read current GUI focus panel."""
        sp = StatusParser()
        focus = sp.get_gui_focus()
        focus_names = {
            0: "NoFocus", 1: "InternalPanel(right)", 2: "ExternalPanel(left)",
            3: "CommsPanel(top)", 4: "RolePanel(bottom)", 5: "StationServices",
            6: "GalaxyMap", 7: "SystemMap", 8: "Orrery", 9: "FSS",
            10: "SAA", 11: "Codex"
        }
        name = focus_names.get(focus, f"Unknown({focus})")
        print(f"\n  GUI Focus: {focus} = {name}")
        self.assertIsInstance(focus, int)


if __name__ == '__main__':
    unittest.main()
