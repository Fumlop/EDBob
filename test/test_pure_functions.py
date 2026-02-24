"""Unit tests for pure functions that require NO game, no files, no screen.

Usage:
    python -m pytest test/test_pure_functions.py -v
"""
import unittest
from json import dumps


# ---------------------------------------------------------------------------
# EDJournal pure functions
# ---------------------------------------------------------------------------
from src.ed.EDJournal import (
    get_ship_size, get_ship_fullname, _has_module,
    check_fuel_scoop, check_adv_docking_computer,
    check_std_docking_computer, check_sco_fsd,
    check_station_type, StationType, EDJournal,
)


class TestGetShipSize(unittest.TestCase):
    def test_known_ships(self):
        self.assertEqual(get_ship_size('sidewinder'), 'S')
        self.assertEqual(get_ship_size('python'), 'M')
        self.assertEqual(get_ship_size('anaconda'), 'L')
        self.assertEqual(get_ship_size('diamondbackxl'), 'S')

    def test_case_insensitive(self):
        self.assertEqual(get_ship_size('Anaconda'), 'L')
        self.assertEqual(get_ship_size('PYTHON'), 'M')

    def test_unknown_ship(self):
        self.assertEqual(get_ship_size('nonexistent_ship'), '')


class TestGetShipFullname(unittest.TestCase):
    def test_known_ships(self):
        self.assertEqual(get_ship_fullname('anaconda'), 'Anaconda')
        self.assertEqual(get_ship_fullname('diamondbackxl'), 'Diamondback Explorer')

    def test_case_insensitive(self):
        self.assertEqual(get_ship_fullname('Anaconda'), 'Anaconda')

    def test_unknown_ship(self):
        self.assertEqual(get_ship_fullname('nonexistent'), '')


class TestHasModule(unittest.TestCase):
    MODULES = [
        {'Slot': 'Slot01_Size6', 'Item': 'int_fuelscoop_size6_class5'},
        {'Slot': 'FrameShiftDrive', 'Item': 'int_hyperdrive_overcharge_size5_class5'},
        {'Slot': 'Slot02_Size5', 'Item': 'int_dockingcomputer_advanced'},
    ]

    def test_finds_module(self):
        self.assertTrue(_has_module(self.MODULES, 'fuelscoop'))

    def test_finds_module_with_slot(self):
        self.assertTrue(_has_module(self.MODULES, 'overcharge', slot='FrameShiftDrive'))

    def test_wrong_slot(self):
        self.assertFalse(_has_module(self.MODULES, 'overcharge', slot='Slot01_Size6'))

    def test_not_found(self):
        self.assertFalse(_has_module(self.MODULES, 'dockingcomputer_standard'))

    def test_none_modules_returns_true(self):
        self.assertTrue(_has_module(None, 'anything'))

    def test_empty_modules(self):
        self.assertFalse(_has_module([], 'fuelscoop'))


class TestModuleCheckers(unittest.TestCase):
    MODULES_FULL = [
        {'Slot': 'Slot01', 'Item': 'int_fuelscoop_size6_class5'},
        {'Slot': 'Slot02', 'Item': 'int_dockingcomputer_advanced'},
        {'Slot': 'FrameShiftDrive', 'Item': 'int_hyperdrive_overcharge_size5'},
    ]
    MODULES_MINIMAL = [
        {'Slot': 'Slot01', 'Item': 'int_cargorack_size4'},
    ]

    def test_fuel_scoop_present(self):
        self.assertTrue(check_fuel_scoop(self.MODULES_FULL))

    def test_fuel_scoop_absent(self):
        self.assertFalse(check_fuel_scoop(self.MODULES_MINIMAL))

    def test_adv_dock_present(self):
        self.assertTrue(check_adv_docking_computer(self.MODULES_FULL))

    def test_adv_dock_absent(self):
        self.assertFalse(check_adv_docking_computer(self.MODULES_MINIMAL))

    def test_std_dock_absent(self):
        self.assertFalse(check_std_docking_computer(self.MODULES_FULL))

    def test_std_dock_present(self):
        mods = [{'Slot': 'Slot01', 'Item': 'int_dockingcomputer_standard'}]
        self.assertTrue(check_std_docking_computer(mods))

    def test_sco_fsd_present(self):
        self.assertTrue(check_sco_fsd(self.MODULES_FULL))

    def test_sco_fsd_wrong_slot(self):
        mods = [{'Slot': 'Slot01', 'Item': 'int_hyperdrive_overcharge_size5'}]
        self.assertFalse(check_sco_fsd(mods))

    def test_none_assumes_fitted(self):
        self.assertTrue(check_fuel_scoop(None))
        self.assertTrue(check_sco_fsd(None))


class TestCheckStationType(unittest.TestCase):
    def test_coriolis(self):
        self.assertEqual(check_station_type('Coriolis', 'Some Station', []), StationType.Starport)

    def test_orbis(self):
        self.assertEqual(check_station_type('Orbis', 'X', []), StationType.Starport)

    def test_outpost(self):
        self.assertEqual(check_station_type('Outpost', 'X', []), StationType.Outpost)

    def test_fleet_carrier(self):
        self.assertEqual(check_station_type('FleetCarrier', 'X', []), StationType.FleetCarrier)

    def test_squadron_carrier(self):
        result = check_station_type('FleetCarrier', 'X', ['SquadronBank', 'dock'])
        self.assertEqual(result, StationType.SquadronCarrier)

    def test_surface_station(self):
        self.assertEqual(check_station_type('SurfaceStation', 'X', []), StationType.SurfaceStation)

    def test_colonisation_ship(self):
        result = check_station_type('SurfaceStation', 'ColonisationShip ABC', [])
        self.assertEqual(result, StationType.ColonisationShip)

    def test_space_construction_depot(self):
        self.assertEqual(check_station_type('SpaceConstructionDepot', 'X', []),
                         StationType.SpaceConstructionDepot)

    def test_crater_outpost(self):
        self.assertEqual(check_station_type('CraterOutpost', 'X', []), StationType.SurfaceStation)

    def test_unknown(self):
        self.assertEqual(check_station_type('SomethingNew', 'X', []), StationType.Unknown)

    def test_case_insensitive(self):
        self.assertEqual(check_station_type('CORIOLIS', 'X', []), StationType.Starport)


class TestTryParse(unittest.TestCase):
    def test_valid_json(self):
        line = '{"event": "FSDJump", "StarSystem": "Sol"}\n'
        result = EDJournal._try_parse(line, None)
        self.assertEqual(result['event'], 'FSDJump')
        self.assertEqual(result['StarSystem'], 'Sol')

    def test_invalid_json(self):
        result = EDJournal._try_parse('not json\n', None)
        self.assertIsNone(result)

    def test_empty_line(self):
        result = EDJournal._try_parse('\n', None)
        self.assertIsNone(result)

    def test_partial_join(self):
        partial = '{"event": "Test",'
        line = '"value": 42}\n'
        result = EDJournal._try_parse(line, partial)
        self.assertEqual(result['event'], 'Test')
        self.assertEqual(result['value'], 42)

    def test_partial_join_fails_tries_line(self):
        partial = 'garbage'
        line = '{"event": "OK"}\n'
        result = EDJournal._try_parse(line, partial)
        self.assertEqual(result['event'], 'OK')

    def test_fragment_no_brace(self):
        result = EDJournal._try_parse('just a fragment\n', None)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Ship.py pure functions
# ---------------------------------------------------------------------------
from src.ship.Ship import Ship, _scale


class TestScale(unittest.TestCase):
    def test_midpoint(self):
        self.assertAlmostEqual(_scale(5, 0, 10, 0, 100), 50.0)

    def test_identity(self):
        self.assertAlmostEqual(_scale(3, 0, 10, 0, 10), 3.0)

    def test_reverse_range(self):
        self.assertAlmostEqual(_scale(0, 0, 10, 100, 0), 100.0)
        self.assertAlmostEqual(_scale(10, 0, 10, 100, 0), 0.0)

    def test_offset(self):
        self.assertAlmostEqual(_scale(5, 0, 10, 10, 20), 15.0)


class TestRollOnCenterline(unittest.TestCase):
    def test_near_zero(self):
        self.assertTrue(Ship._roll_on_centerline(2.0, 5.0))
        self.assertTrue(Ship._roll_on_centerline(-3.0, 5.0))

    def test_near_180(self):
        self.assertTrue(Ship._roll_on_centerline(178.0, 5.0))
        self.assertTrue(Ship._roll_on_centerline(-177.0, 5.0))

    def test_far_from_centerline(self):
        self.assertFalse(Ship._roll_on_centerline(90.0, 5.0))
        self.assertFalse(Ship._roll_on_centerline(-45.0, 5.0))

    def test_exact_boundary(self):
        self.assertTrue(Ship._roll_on_centerline(5.0, 5.1))
        self.assertFalse(Ship._roll_on_centerline(5.1, 5.0))


class TestAxisPickKey(unittest.TestCase):
    """Test _axis_pick_key -- needs a Ship instance but no real dependencies."""

    def setUp(self):
        # Minimal Ship with no real deps
        class FakeKeys:
            pass
        class FakeStatus:
            def get_flag(self, f): return False
        self.ship = Ship.__new__(Ship)
        # Only need the static-like method, but it reads self -- use instance

    def test_roll_positive(self):
        self.assertEqual(Ship._axis_pick_key(None, 'roll', 30.0), 'RollRightButton')

    def test_roll_negative(self):
        self.assertEqual(Ship._axis_pick_key(None, 'roll', -30.0), 'RollLeftButton')

    def test_pitch_up(self):
        self.assertEqual(Ship._axis_pick_key(None, 'pit', 20.0), 'PitchUpButton')

    def test_pitch_down(self):
        self.assertEqual(Ship._axis_pick_key(None, 'pit', -20.0), 'PitchDownButton')

    def test_pitch_over_90_inverts(self):
        # When pitch > 90, direction inverts (target is behind)
        self.assertEqual(Ship._axis_pick_key(None, 'pit', 120.0), 'PitchDownButton')
        self.assertEqual(Ship._axis_pick_key(None, 'pit', -120.0), 'PitchUpButton')

    def test_yaw_right(self):
        self.assertEqual(Ship._axis_pick_key(None, 'yaw', 10.0), 'YawRightButton')

    def test_yaw_left(self):
        self.assertEqual(Ship._axis_pick_key(None, 'yaw', -10.0), 'YawLeftButton')


class TestGetDist(unittest.TestCase):
    def setUp(self):
        self.ship = Ship.__new__(Ship)

    def test_pitch(self):
        self.assertEqual(self.ship._get_dist('pit', {'pit': 15.3}), 16)  # ceil

    def test_yaw(self):
        self.assertEqual(self.ship._get_dist('yaw', {'yaw': -7.1}), 8)  # ceil(abs)

    def test_roll_near_zero(self):
        self.assertEqual(self.ship._get_dist('roll', {'roll': 12.5}), 13)

    def test_roll_near_180(self):
        # 170 deg off -> min(170, 180-170) = 10
        self.assertEqual(self.ship._get_dist('roll', {'roll': 170.0}), 10)

    def test_roll_negative(self):
        self.assertEqual(self.ship._get_dist('roll', {'roll': -5.2}), 6)


class TestIsAligned(unittest.TestCase):
    def setUp(self):
        self.ship = Ship.__new__(Ship)

    def test_pitch_aligned(self):
        self.assertTrue(self.ship._is_aligned('pit', {'pit': 2.0}, 5.0))

    def test_pitch_not_aligned(self):
        self.assertFalse(self.ship._is_aligned('pit', {'pit': 10.0}, 5.0))

    def test_yaw_aligned(self):
        self.assertTrue(self.ship._is_aligned('yaw', {'yaw': -3.0}, 5.0))

    def test_roll_aligned_near_zero(self):
        self.assertTrue(self.ship._is_aligned('roll', {'roll': 2.0}, 5.0))

    def test_roll_aligned_near_180(self):
        self.assertTrue(self.ship._is_aligned('roll', {'roll': 178.0}, 5.0))

    def test_roll_not_aligned(self):
        self.assertFalse(self.ship._is_aligned('roll', {'roll': 90.0}, 5.0))


class TestFuelPercent(unittest.TestCase):
    def setUp(self):
        self.ship = Ship.__new__(Ship)

    def test_full_tank(self):
        self.ship.fuel_level = 32.0
        self.ship.fuel_capacity = 32.0
        self.ship._update_fuel_percent()
        self.assertEqual(self.ship.fuel_percent, 100)

    def test_half_tank(self):
        self.ship.fuel_level = 16.0
        self.ship.fuel_capacity = 32.0
        self.ship._update_fuel_percent()
        self.assertEqual(self.ship.fuel_percent, 50)

    def test_no_data_defaults_10(self):
        self.ship.fuel_level = None
        self.ship.fuel_capacity = None
        self.ship._update_fuel_percent()
        self.assertEqual(self.ship.fuel_percent, 10)

    def test_zero_fuel(self):
        self.ship.fuel_level = 0
        self.ship.fuel_capacity = 32.0
        self.ship._update_fuel_percent()
        # 0 is falsy, so falls to default
        self.assertEqual(self.ship.fuel_percent, 10)

    def test_rounding(self):
        self.ship.fuel_level = 10.0
        self.ship.fuel_capacity = 32.0
        self.ship._update_fuel_percent()
        self.assertEqual(self.ship.fuel_percent, 31)  # 31.25 rounds to 31


# ---------------------------------------------------------------------------
# Screen_Regions.py geometry
# ---------------------------------------------------------------------------
from src.screen.Screen_Regions import Point, Quad


class TestPoint(unittest.TestCase):
    def test_init(self):
        p = Point(3.0, 4.0)
        self.assertEqual(p.x, 3.0)
        self.assertEqual(p.y, 4.0)

    def test_getters(self):
        p = Point(1.5, 2.5)
        self.assertEqual(p.get_x(), 1.5)
        self.assertEqual(p.get_y(), 2.5)

    def test_to_list(self):
        self.assertEqual(Point(1, 2).to_list(), [1, 2])

    def test_from_xy(self):
        p = Point.from_xy((10, 20))
        self.assertEqual(p.x, 10)
        self.assertEqual(p.y, 20)

    def test_from_list(self):
        p = Point.from_list([5, 6])
        self.assertEqual(p.x, 5)
        self.assertEqual(p.y, 6)

    def test_str(self):
        self.assertEqual(str(Point(1, 2)), "Point(1, 2)")


class TestQuad(unittest.TestCase):
    def _rect_quad(self, l=0, t=0, r=100, b=50):
        return Quad.from_rect([l, t, r, b])

    def test_from_rect(self):
        q = self._rect_quad(10, 20, 110, 70)
        self.assertEqual(q.get_left(), 10)
        self.assertEqual(q.get_top(), 20)
        self.assertEqual(q.get_right(), 110)
        self.assertEqual(q.get_bottom(), 70)

    def test_from_list(self):
        q = Quad.from_list([[0, 0], [100, 0], [100, 50], [0, 50]])
        self.assertEqual(q.get_width(), 100)
        self.assertEqual(q.get_height(), 50)

    def test_dimensions(self):
        q = self._rect_quad(0, 0, 200, 100)
        self.assertEqual(q.get_width(), 200)
        self.assertEqual(q.get_height(), 100)

    def test_center(self):
        q = self._rect_quad(0, 0, 100, 50)
        c = q.get_center()
        self.assertEqual(c.x, 50.0)
        self.assertEqual(c.y, 25.0)

    def test_bounds(self):
        q = self._rect_quad(10, 20, 30, 40)
        tl, br = q.get_bounds()
        self.assertEqual(tl.x, 10)
        self.assertEqual(tl.y, 20)
        self.assertEqual(br.x, 30)
        self.assertEqual(br.y, 40)

    def test_to_rect_list(self):
        q = self._rect_quad(5, 10, 15, 20)
        self.assertEqual(q.to_rect_list(), [5, 10, 15, 20])

    def test_to_rect_list_rounded(self):
        q = Quad(Point(1.234, 5.678), Point(9.012, 5.678),
                 Point(9.012, 3.456), Point(1.234, 3.456))
        result = q.to_rect_list(round_dp=1)
        self.assertEqual(result, [1.2, 3.5, 9.0, 5.7])

    def test_to_list(self):
        q = self._rect_quad(0, 0, 10, 5)
        pts = q.to_list()
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0], [0, 0])
        self.assertEqual(pts[2], [10, 5])

    def test_offset(self):
        q = self._rect_quad(0, 0, 100, 50)
        q.offset(10, 20)
        self.assertEqual(q.get_left(), 10)
        self.assertEqual(q.get_top(), 20)
        self.assertEqual(q.get_right(), 110)
        self.assertEqual(q.get_bottom(), 70)

    def test_scale(self):
        q = self._rect_quad(0, 0, 100, 50)
        # Center is (50, 25). Scale 2x from center.
        q.scale(2.0, 2.0)
        self.assertAlmostEqual(q.get_left(), -50.0)
        self.assertAlmostEqual(q.get_right(), 150.0)
        self.assertAlmostEqual(q.get_top(), -25.0)
        self.assertAlmostEqual(q.get_bottom(), 75.0)

    def test_scale_preserves_center(self):
        q = self._rect_quad(10, 20, 110, 70)
        c_before = q.get_center()
        q.scale(1.5, 0.5)
        c_after = q.get_center()
        self.assertAlmostEqual(c_before.x, c_after.x)
        self.assertAlmostEqual(c_before.y, c_after.y)

    def test_scale_from_origin(self):
        q = self._rect_quad(10, 20, 30, 40)
        q.scale_from_origin(2.0, 2.0)
        self.assertEqual(q.get_left(), 20)
        self.assertEqual(q.get_top(), 40)
        self.assertEqual(q.get_right(), 60)
        self.assertEqual(q.get_bottom(), 80)

    def test_inflate(self):
        q = self._rect_quad(10, 10, 50, 30)
        # center = (30, 20). Inflate by 5 in each direction.
        q.inflate(5, 5)
        self.assertAlmostEqual(q.get_left(), 5)
        self.assertAlmostEqual(q.get_right(), 55)
        self.assertAlmostEqual(q.get_top(), 5)
        self.assertAlmostEqual(q.get_bottom(), 35)

    def test_subregion_full(self):
        q = self._rect_quad(0, 0, 100, 50)
        sub = Quad.from_rect([0.0, 0.0, 1.0, 1.0])
        q.subregion_from_quad(sub)
        self.assertAlmostEqual(q.get_left(), 0.0)
        self.assertAlmostEqual(q.get_right(), 100.0)

    def test_subregion_quarter(self):
        q = self._rect_quad(0, 0, 100, 100)
        sub = Quad.from_rect([0.0, 0.0, 0.5, 0.5])
        q.subregion_from_quad(sub)
        self.assertAlmostEqual(q.get_left(), 0.0)
        self.assertAlmostEqual(q.get_top(), 0.0)
        self.assertAlmostEqual(q.get_right(), 50.0)
        self.assertAlmostEqual(q.get_bottom(), 50.0)

    def test_get_top_left(self):
        q = self._rect_quad(5, 10, 15, 20)
        tl = q.get_top_left()
        self.assertEqual(tl.x, 5)
        self.assertEqual(tl.y, 10)

    def test_get_bottom_right(self):
        q = self._rect_quad(5, 10, 15, 20)
        br = q.get_bottom_right()
        self.assertEqual(br.x, 15)
        self.assertEqual(br.y, 20)


if __name__ == '__main__':
    unittest.main()
