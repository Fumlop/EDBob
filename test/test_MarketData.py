"""Standalone market data parsing test.

Does NOT require Elite Dangerous to be running.
Reads Market.json and Cargo.json from the journal folder.

Usage:
    ./venv/Scripts/python -m pytest test/test_MarketData.py -s
"""
import unittest


class MarketDataTestCase(unittest.TestCase):

    def test_load_market_data(self):
        """Load and display market data."""
        from src.ed.MarketParser import MarketParser
        mp = MarketParser()
        data = mp.get_market_data()

        if data is None:
            self.skipTest("No Market.json found (visit a station first)")

        print(f"\n  Station: {mp.get_market_name()}")
        print(f"  Items: {len(data.get('Items', []))}")

    def test_buyable_items(self):
        """List items available for purchase."""
        from src.ed.MarketParser import MarketParser
        mp = MarketParser()
        items = mp.get_buyable_items()

        if items is None:
            self.skipTest("No market data or no buyable items")

        print(f"\n  Buyable items: {len(items)}")
        for i, item in enumerate(items):
            print(f"    [{i:2d}] {item['Name_Localised']:<30} "
                  f"stock={item['Stock']:>6}  price={item.get('BuyPrice', '?'):>8}")
        self.assertGreater(len(items), 0)

    def test_item_details(self):
        """Query details of first buyable item."""
        from src.ed.MarketParser import MarketParser
        mp = MarketParser()
        items = mp.get_buyable_items()

        if not items:
            self.skipTest("No buyable items")

        name = items[0]['Name_Localised']
        detail = mp.get_item(name)
        print(f"\n  Item detail for '{name}':")
        if detail:
            for k, v in detail.items():
                print(f"    {k}: {v}")
        self.assertIsNotNone(detail)

    def test_load_cargo_data(self):
        """Load and display cargo data."""
        from src.ed.CargoParser import CargoParser
        cp = CargoParser()
        data = cp.get_cargo_data()

        if data is None:
            self.skipTest("No Cargo.json found")

        items = cp.get_items()
        print(f"\n  Cargo items: {len(items)}")
        for item in items:
            print(f"    {item.get('Name_Localised', item.get('Name', '?')):<30} "
                  f"count={item.get('Count', '?')}")

    def test_nav_route(self):
        """Load and display navigation route."""
        from src.ed.NavRouteParser import NavRouteParser
        nrp = NavRouteParser()
        data = nrp.get_nav_route_data()

        if data is None:
            self.skipTest("No NavRoute.json found")

        last = nrp.get_last_system()
        route = data.get('Route', [])
        print(f"\n  Route systems: {len(route)}")
        if route:
            print(f"  Start: {route[0].get('StarSystem', '?')}")
            print(f"  End:   {last}")
        for i, sys in enumerate(route):
            print(f"    [{i}] {sys.get('StarSystem', '?')} "
                  f"({sys.get('StarClass', '?')})")


if __name__ == '__main__':
    unittest.main()
