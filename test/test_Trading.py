"""Standalone trading test.

Requires Elite Dangerous running, docked at a station.
You should be at the main cockpit view (not already in a menu).

Usage:
    ./venv/Scripts/python -m pytest test/test_Trading.py -s -k test_buy_incremental
    ./venv/Scripts/python -m pytest test/test_Trading.py -s -k test_ocr_quantity_only
"""
import unittest
from time import sleep, time
from test.test_helpers import create_autopilot


class TradingTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ed_ap = create_autopilot()

    def _check_docked(self):
        from src.core.EDAP_data import FlagsDocked
        if not self.ed_ap.scr.elite_window_exists():
            self.skipTest("Elite Dangerous window not found")
        if not self.ed_ap.status.get_flag(FlagsDocked):
            self.skipTest("Not docked at a station")

    def test_buy_incremental(self):
        """Buy commodities with increasing qty targets, log everything."""
        self._check_docked()
        from src.ed.EDStationServicesInShip import EDStationServicesInShip

        ap = self.ed_ap
        stn_svc = EDStationServicesInShip(ap, ap.scr, ap.keys, cb=ap.ap_ckb)

        cargo_capacity = ap.jn.ship_state()['cargo_capacity']
        curr_cargo = int(ap.status.get_cleaned_data()['Cargo'])
        free_cargo = cargo_capacity - curr_cargo
        print(f"\n=== CARGO STATUS ===")
        print(f"  Capacity: {cargo_capacity}, Current: {curr_cargo}, Free: {free_cargo}")

        if free_cargo == 0:
            self.skipTest("Cargo is full, nothing to buy")

        print(f"\n=== ENTERING COMMODITIES MARKET ===")
        res = stn_svc.goto_commodities_market()
        self.assertTrue(res, "Could not access commodities market")

        cm = stn_svc.commodities_market
        cm.select_buy(ap.keys)
        sleep(1.0)

        items = cm.market_parser.get_buyable_items()
        if not items:
            self.skipTest("No buyable items")

        print(f"  Found {len(items)} buyable commodities")
        for i, item in enumerate(items):
            print(f"    [{i}] {item['Name_Localised']} - stock: {item['Stock']}")

        print(f"\n=== BUYING PHASE ===")
        results = []
        qty_step = 100

        for idx, item in enumerate(items):
            name = item['Name_Localised']
            stock = item['Stock']
            target_qty = min((idx + 1) * qty_step, free_cargo)

            if target_qty <= 0:
                print(f"\n  [{idx}] {name}: No cargo space left, stopping")
                break

            actual_buy = min(target_qty, stock, free_cargo)
            print(f"\n  [{idx}] {name}: target={target_qty}, stock={stock}, "
                  f"free={free_cargo}, will_buy={actual_buy}")

            t0 = time()
            success, bought = cm.buy_commodity(ap.keys, name, target_qty, free_cargo)
            elapsed = time() - t0

            if success and bought > 0:
                free_cargo -= bought

            results.append({
                'name': name,
                'target': target_qty,
                'stock': stock,
                'bought': bought,
                'success': success,
                'time_s': elapsed,
            })

            print(f"  [{idx}] Result: success={success}, bought={bought}, "
                  f"time={elapsed:.1f}s, free_after={free_cargo}")

            sleep(1.0)

            if free_cargo <= 0:
                print(f"  Cargo full, stopping")
                break

        print(f"\n=== RESULTS SUMMARY ===")
        print(f"  {'Name':<30} {'Target':>6} {'Bought':>6} {'Time':>6} {'OK':>4}")
        print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*6} {'-'*4}")
        total_bought = 0
        for r in results:
            print(f"  {r['name']:<30} {r['target']:>6} {r['bought']:>6} "
                  f"{r['time_s']:>5.1f}s {'Y' if r['success'] else 'N':>4}")
            total_bought += r['bought']
        print(f"\n  Total bought: {total_bought}")
        print(f"  Remaining cargo: {free_cargo}")

    def test_ocr_quantity_only(self):
        """Just test OCR reading of the quantity field.
        You must manually open a buy popup before running this.
        """
        self._check_docked()
        from src.ed.EDStationServicesInShip import CommoditiesMarket

        ap = self.ed_ap
        cm = CommoditiesMarket(ap, ap.scr, ap.keys, cb=ap.ap_ckb)

        print(f"\n=== OCR QUANTITY TEST ===")
        print("  Make sure a buy/sell popup is open!")
        sleep(2.0)

        for i in range(5):
            t0 = time()
            val = cm._ocr_quantity()
            elapsed = time() - t0
            print(f"  Read [{i+1}]: value={val}, time={elapsed:.2f}s")
            sleep(0.5)


if __name__ == '__main__':
    unittest.main()
