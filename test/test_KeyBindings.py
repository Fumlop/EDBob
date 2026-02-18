"""Standalone key binding validation test.

Does NOT require Elite Dangerous to be running.
Tests binding file discovery, parsing, and collision detection.

Usage:
    ./venv/Scripts/python -m pytest test/test_KeyBindings.py -s
"""
import unittest


def dummy_cb(msg, body=None):
    if body:
        print(f"[CB] {msg}: {body}")
    else:
        print(f"[CB] {msg}")


class KeyBindingsTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src.ed.EDKeys import EDKeys
        cls.keys = EDKeys(cb=dummy_cb)

    def test_load_bindings(self):
        """Load and display key bindings."""
        bindings = self.keys.get_bindings()
        print(f"\n  Loaded {len(bindings)} bindings")
        for name, key in sorted(bindings.items()):
            print(f"    {name:<30}: {key}")
        self.assertGreater(len(bindings), 0, "No bindings loaded")

    def test_essential_bindings_exist(self):
        """Check all essential autopilot bindings are present."""
        bindings = self.keys.get_bindings()
        essential = [
            'PitchUpButton', 'PitchDownButton',
            'RollLeftButton', 'RollRightButton',
            'YawLeftButton', 'YawRightButton',
            'SetSpeedZero', 'SetSpeed100',
            'UI_Up', 'UI_Down', 'UI_Left', 'UI_Right', 'UI_Select',
            'HyperSuperCombination',
        ]
        print()
        missing = []
        for name in essential:
            if name in bindings:
                print(f"  OK   {name:<30}: {bindings[name]}")
            else:
                print(f"  MISS {name}")
                missing.append(name)

        if missing:
            print(f"\n  WARNING: Missing bindings: {missing}")
        self.assertEqual(len(missing), 0, f"Missing essential bindings: {missing}")

    def test_key_collisions(self):
        """Check for key binding collisions on important keys."""
        bindings = self.keys.get_bindings()
        keys_to_check = [
            'UI_Up', 'UI_Down', 'UI_Left', 'UI_Right', 'UI_Select',
            'SetSpeedZero', 'SetSpeed50', 'SetSpeed100',
        ]
        print()
        found_collisions = False
        for name in keys_to_check:
            collisions = self.keys.get_collisions(name)
            if collisions:
                print(f"  COLLISION {name}: {collisions}")
                found_collisions = True
            else:
                print(f"  OK       {name}: no collisions")

        if found_collisions:
            print("\n  WARNING: Some key collisions found (may cause issues)")

    def test_hotkey_check(self):
        """Check hotkey binding types."""
        hotkeys = ['SetSpeedZero', 'SetSpeed50', 'SetSpeed100', 'SetSpeed25', 'SetSpeed75']
        print()
        for name in hotkeys:
            result = self.keys.check_hotkey_in_bindings(name)
            print(f"  {name:<20}: {result if result else 'NOT BOUND'}")


if __name__ == '__main__':
    unittest.main()
