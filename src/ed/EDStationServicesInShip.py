from __future__ import annotations
import json
import os
from copy import copy

import cv2

from src.core.EDAP_data import GuiFocusStationServices
from src.ed.EDJournal import StationType
from src.ed.MarketParser import MarketParser
from src.ed.StatusParser import StatusParser
from src.ed import MenuNav
from time import sleep
from src.core.EDlogger import logger
from src.screen.Screen_Regions import Quad, scale_region, load_calibrated_regions

"""
File:StationServicesInShip.py    

Description:
  TBD 

Author: Stumpii
"""


class EDStationServicesInShip:
    """ Handles Station Services In Ship. """
    def __init__(self, ed_ap, screen, keys, cb):
        self.ap = ed_ap
        self.ocr = ed_ap.ocr
        self.locale = self.ap.locale
        self.screen = screen
        self.keys = keys
        self.ap_ckb = cb
        self.passenger_lounge = PassengerLounge(self, self.ap, self.ocr, self.keys, self.screen, self.ap_ckb)
        self.commodities_market = CommoditiesMarket(self, self.ap, self.ocr, self.keys, self.screen, self.ap_ckb)
        self.status_parser = StatusParser()
        self.market_parser = MarketParser()
        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        self.reg = {'commodities_market': {'rect': [0.0, 0.0, 0.25, 0.25]},
                    'station_services': {'rect': [0.10, 0.10, 0.90, 0.85]},
                    'connected_to': {'rect': [0.0, 0.0, 0.25, 0.1]},
                    'title': {'rect': [0.0, 0.0, 1.0, 1.0]},
                    'commodity_column': {'rect': [0.0, 0.0, 1.0, 1.0]},
                    'buy_qty_box': {'rect': [0.0, 0.0, 1.0, 1.0]},
                    'sell_qty_box': {'rect': [0.0, 0.0, 1.0, 1.0]},
                    'commodity_name': {'rect': [0.0, 0.0, 1.0, 1.0]},
                    }

        # Load custom regions from file
        load_calibrated_regions('EDStationServicesInShip', self.reg)

    def goto_station_services(self) -> bool:
        """ Goto Station Services. Delegates to MenuNav.open_station_services. """
        res = MenuNav.open_station_services(self.keys, self.status_parser)

        if res and self.ap.debug_overlay:
            stn_svcs = Quad.from_rect(self.reg['station_services']['rect'])
            self.ap.overlay.overlay_quad_pct('stn_svcs', stn_svcs, (0, 255, 0), 2, 5)
            self.ap.overlay.overlay_paint()

        return res

    def goto_construction_services(self) -> bool:
        """ Goto Construction Services. This is for an Orbital Construction Site.
        Same menu path as Station Services, just no GuiFocus wait.
        """
        MenuNav.goto_cockpit(self.keys, self.status_parser)
        MenuNav.realign_cursor(self.keys, hold=3)
        sleep(0.3)
        self.keys.send("UI_Select")  # select refuel line
        sleep(0.3)
        self.keys.send("UI_Down")    # construction services
        self.keys.send("UI_Select")  # open it

        # TODO - replace with OCR from OCR branch?
        sleep(3)  # wait for new menu to finish rendering

        return True

    def determine_commodities_location(self) -> str:
        """ Get the services layout as the layout may be different per station.
        There is probably a better way to do this!
        @return: The string of the positions (i.e. RRD for Right-Right-Down).
        """
        station_type = self.ap.jn.ship_state()['exp_station_type']
        # CONNECTED TO menu is different between stations and fleet carriers
        if station_type == StationType.FleetCarrier:
            # Fleet Carrier COMMODITIES MARKET location top right, with:
            # uni cart, redemption, tritium depot, shipyard, crew lounge
            return "RR"

        elif station_type == StationType.SquadronCarrier:
            # Fleet Carrier COMMODITIES MARKET location top right, with:
            # uni cart, redemption, tritium depot, shipyard, crew lounge
            return "RD"

        elif station_type == StationType.Outpost:
            # Outpost COMMODITIES MARKET location in middle column
            return "R"

        else:
            # Orbital station COMMODITIES MARKET location bottom left
            return "D"

    def goto_commodities_market(self) -> bool:
        """ Go to the COMMODITIES market. """
        # Go down to station services
        res = self.goto_station_services()
        if not res:
            return False

        # Try to determine commodities button on the services screen. Have seen it below Mission Board and too
        # right of the mission board.
        res = self.determine_commodities_location()
        if res == "":
            logger.warning("Unable to find COMMODITIES MARKET button on Station Services screen.")
            return False

        self.ap_ckb('log+vce', "Connecting to commodities market.")
        sleep(5)  # Wait for station services welcome screen to finish rendering

        # Select Mission Board
        if res == "RR":
            # Fleet Carrier COMMODITIES MARKET location top right, with:
            # uni cart, redemption, tritium depot, shipyard, crew lounge
            self.keys.send('UI_Right', repeat=2)
            sleep(0.3)
            self.keys.send('UI_Select')  # Select Commodities

        elif res == "RD":
            # Squadron Fleet Carrier COMMODITIES MARKET location right and one down
            self.keys.send('UI_Right')
            sleep(0.3)
            self.keys.send('UI_Down')
            sleep(0.3)
            self.keys.send('UI_Select')  # Select Commodities

        elif res == "R":
            # Outpost COMMODITIES MARKET location in middle column
            self.keys.send('UI_Right')
            sleep(0.3)
            self.keys.send('UI_Select')  # Select Commodities

        elif res == "D":
            # Orbital station COMMODITIES MARKET location bottom left
            self.keys.send('UI_Down')
            sleep(0.3)
            self.keys.send('UI_Select')  # Select Commodities

        # Wait for market screen transition. The actual "market loaded" check
        # happens in EDWayPoint via Market.json timestamp polling.
        sleep(2)
        return True

    @staticmethod
    def sell_to_colonisation_ship(ap):
        """ Sell all cargo to a colonisation/construction ship. Delegates to MenuNav. """
        MenuNav.transfer_all_to_colonisation(ap.keys)


class PassengerLounge:
    def __init__(self, station_services_in_ship: EDStationServicesInShip, ed_ap, ocr, keys, screen, cb):
        self.parent = station_services_in_ship
        self.ap = ed_ap
        self.ocr = ocr
        self.keys = keys
        self.screen = screen
        self.ap_ckb = cb

        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        # Nav Panel region covers the entire navigation panel.
        self.reg = {'no_cmpl_missions': {'rect': [0.47, 0.77, 0.675, 0.85]},
                    'mission_dest_col': {'rect': [0.47, 0.41, 0.64, 0.85]},
                    'complete_mission_col': {'rect': [0.47, 0.22, 0.675, 0.85]}}

        self.no_cmpl_missions_row_width = 384  # Buy/sell item width in pixels at 1920x1080
        self.no_cmpl_missions_row_height = 70  # Buy/sell item height in pixels at 1920x1080
        self.mission_dest_row_width = 326  # Buy/sell item width in pixels at 1920x1080
        self.mission_dest_row_height = 70  # Buy/sell item height in pixels at 1920x1080
        self.complete_mission_row_width = 384  # Buy/sell item width in pixels at 1920x1080
        self.complete_mission_row_height = 70  # Buy/sell item height in pixels at 1920x1080


class CommoditiesMarket:
    def __init__(self, station_services_in_ship: EDStationServicesInShip, ed_ap, ocr, keys, screen, cb):
        self.parent = station_services_in_ship
        self.ap = ed_ap
        self.ocr = ocr
        self.keys = keys
        self.screen = screen
        self.ap_ckb = cb

        self.market_parser = MarketParser()
        # The reg rect is top left x, y, and bottom right x, y in fraction of screen resolution at 1920x1080
        self.reg = {'cargo_col': {'rect': [0.13, 0.227, 0.19, 0.90]},
                    'commodity_name_col': {'rect': [0.19, 0.227, 0.41, 0.90]},
                    'supply_demand_col': {'rect': [0.42, 0.227, 0.49, 0.90]}}
        self.commodity_row_width = 422  # Buy/sell item width in pixels at 1920x1080
        self.commodity_row_height = 35  # Buy/sell item height in pixels at 1920x1080
        self._cursor_pos = 0  # current row in commodity list

    def _ocr_quantity(self) -> int:
        """Read the buy/sell quantity from the screen using OCR.
        Returns the current quantity value, or -1 if OCR fails.
        The quantity field shows 'NNN / MAX' -- we want the left number.
        """
        import numpy as np
        try:
            import easyocr
        except ImportError:
            return -1

        # Capture the quantity input box (left number only, we already know max)
        img = self.screen.get_screen_full()
        # Crop the quantity input box (NNN/MAX field inside buy popup)
        # Absolute pixel coords at 1920x1080, calibrated from OCR Area Value Commodity.png
        x1, x2 = 460, 729
        y1, y2 = 356, 421
        crop = img[y1:y2, x1:x2]

        # Threshold for orange text on dark background
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # Orange text: H=10-25, S>100, V>150
        mask = cv2.inRange(hsv, np.array([5, 100, 150]), np.array([30, 255, 255]))
        # Also white text
        mask2 = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 40, 255]))
        mask = cv2.bitwise_or(mask, mask2)

        # Make white text on black bg for OCR
        ocr_img = mask

        from src.ed.EDGalaxyMap import _get_ocr_reader
        reader = _get_ocr_reader()
        results = reader.readtext(ocr_img, allowlist='0123456789', detail=0)
        if results:
            # Take only the first detected number (left side = current qty, ignore /MAX)
            digits = ''.join(c for c in results[0] if c.isdigit())
            if digits:
                val = int(digits)
                logger.info(f"OCR quantity: {val} (raw: {results})")
                return val
        logger.info(f"OCR quantity: failed (results: {results})")
        return -1

    def _set_buy_sell_quantity(self, keys, target_qty: int, max_qty: int):
        """Set the buy/sell quantity in the popup dialog.
        If target fills all free cargo, hold right to max.
        Otherwise tap right for exact count.
        """
        target_qty = int(target_qty)
        max_qty = int(max_qty)
        if target_qty >= max_qty:
            keys.send("UI_Right", hold=4)
        else:
            keys.send("UI_Right", hold=0.04, repeat=target_qty)

    def select_buy(self, keys) -> bool:
        """ Select Buy. Assumes on Commodities Market screen. """

        # Select Buy
        keys.send("UI_Left", repeat=2)
        keys.send("UI_Up", repeat=4)

        keys.send("UI_Select")  # Select Buy

        sleep(0.5)  # give time to bring up list
        keys.send('UI_Right')  # Go to top of commodities list
        self._cursor_pos = 0
        return True

    def select_sell(self, keys) -> bool:
        """ Select Sell. Assumes on Commodities Market screen. """

        # Select Sell
        keys.send("UI_Left", repeat=2)
        keys.send("UI_Up", repeat=4)

        keys.send("UI_Down")
        keys.send("UI_Select")  # Select Sell

        sleep(0.5)  # give time to bring up list
        keys.send('UI_Right')  # Go to top of commodities list
        self._cursor_pos = 0
        return True

    def buy_commodity(self, keys, name: str, qty: int, free_cargo: int) -> tuple[bool, int]:
        """ Buy qty of commodity. If qty >= 9999 then buy as much as possible.
        Assumed to be in the commodities buy screen in the list. """

        # If we are updating requirement count, me might have all the qty we need
        if qty <= 0:
            return False, 0

        # Determine if station sells the commodity!
        self.market_parser.get_market_data()
        if not self.market_parser.can_buy_item(name):
            self.ap_ckb('log+vce', f"'{name}' is not sold or has no stock at {self.market_parser.get_market_name()}.")
            logger.debug(f"Item '{name}' is not sold or has no stock at {self.market_parser.get_market_name()}.")
            return False, 0

        # Find commodity in market and return the index
        index = -1
        stock = 0
        buyable_items = self.market_parser.get_buyable_items()
        if buyable_items is not None:
            for i, value in enumerate(buyable_items):
                if value['Name_Localised'].upper() == name.upper():
                    index = i
                    stock = value['Stock']
                    logger.debug(f"Execute trade: Buy {name} (want {qty} of {stock} avail.) at position {index + 1}.")
                    break

        # Actual qty we can sell
        act_qty = min(qty, stock, free_cargo)

        # See if we buy all and if so, remove the item to update the list, as the item will be removed
        # from the commodities screen, but the market.json will not be updated.
        buy_all = act_qty == stock
        if buy_all:
            for i, value in enumerate(self.market_parser.current_data['Items']):
                if value['Name_Localised'].upper() == name.upper():
                    # Set the stock bracket to 0, so it does not get included in available commodities list.
                    self.market_parser.current_data['Items'][i]['StockBracket'] = 0

        if index > -1:
            # Navigate from current cursor position to target index
            delta = index - self._cursor_pos
            logger.info(f"Buy {name}: index={index}, cursor={self._cursor_pos}, delta={delta}")
            if delta > 0:
                keys.send('UI_Down', hold=0.05, repeat=delta)
            elif delta < 0:
                keys.send('UI_Up', hold=0.05, repeat=abs(delta))

            sleep(0.75)
            keys.send('UI_Select')  # Select that commodity

            if self.ap.debug_overlay:
                q = Quad.from_rect(self.parent.reg['buy_qty_box']['rect'])
                self.ap.overlay.overlay_quad_pct('buy_qty_box', q, (0, 255, 0), 2, 5)
                self.ap.overlay.overlay_paint()

            sleep(0.5)  # give time to popup
            keys.send('UI_Up', repeat=2)  # go up to quantity field
            # Log the planned quantity
            self.ap_ckb('log+vce', f"Buying {act_qty} units of {name}.")
            logger.info(f"Attempting to buy {act_qty} units of {name}")

            # Set quantity
            max_qty = max(1, min(stock, free_cargo))
            self._set_buy_sell_quantity(keys, act_qty, max_qty)

            keys.send('UI_Down')
            self.ap.jn.ship['last_market_buy'] = None  # clear before buy so we detect the new event
            keys.send('UI_Select')  # Select Buy

            # Cross-check with journal for actual quantity bought
            actual_qty = act_qty
            for _ in range(10):  # wait up to 2s for MarketBuy event
                sleep(0.2)
                ship = self.ap.jn.ship_state()
                last_buy = ship.get('last_market_buy')
                if last_buy and last_buy['Type'].upper() == name.upper():
                    actual_qty = last_buy['Count']
                    if actual_qty != act_qty:
                        logger.warning(f"Buy {name}: journal says {actual_qty}, planned {act_qty}")
                        self.ap_ckb('log', f"Buy mismatch: got {actual_qty}/{act_qty} {name}")
                    break

            # After buying all stock, item disappears from list
            if buy_all:
                # Item removed, cursor now points to next item at same index
                pass  # cursor_pos stays the same (next item slid up)
            else:
                self._cursor_pos = index

        return True, actual_qty

    def sell_commodity(self, keys, name: str, qty: int, cargo_parser) -> tuple[bool, int]:
        """ Sell qty of commodity. If qty >= 9999 then sell as much as possible.
        Assumed to be in the commodities sell screen in the list.
        @param keys: Keys class for sending keystrokes.
        @param name: Name of the commodity.
        @param qty: Quantity to sell.
        @param cargo_parser: Current cargo to check if rare or demand=1 items exist in hold.
        @return: Sale successful (T/F) and Qty.
        """

        # If we are updating requirement count, me might have sold all we have
        if qty <= 0:
            return False, 0



        # Determine if station buys the commodity!
        self.market_parser.get_market_data()
        if not self.market_parser.can_sell_item(name):
            self.ap_ckb('log+vce', f"'{name}' is not bought at {self.market_parser.get_market_name()}.")
            logger.debug(f"Item '{name}' is not bought at {self.market_parser.get_market_name()}.")
            return False, 0

        # Find commodity in market and return the index
        index = -1
        demand = 0
        sellable_items = self.market_parser.get_sellable_items(cargo_parser)
        if sellable_items is not None:
            for i, value in enumerate(sellable_items):
                if value['Name_Localised'].upper() == name.upper():
                    index = i
                    demand = value['Demand']
                    logger.debug(f"Execute trade: Sell {name} ({qty} of {demand} demanded) at position {index + 1}.")
                    break

        # Check how many of the item do we have.
        qty_in_cargo = 9999
        if cargo_parser.get_item(name) is not None:
            cargo_item = cargo_parser.get_item(name)
            qty_in_cargo = cargo_item['Count']

        # Qty we can sell. Unlike buying, we can sell more than the demand
        # But maybe not at all stations!
        act_qty = min(qty, qty_in_cargo)

        if index > -1:
            # Navigate from current cursor position to target index
            delta = index - self._cursor_pos
            logger.info(f"Sell {name}: index={index}, cursor={self._cursor_pos}, delta={delta}")
            if delta > 0:
                keys.send('UI_Down', hold=0.05, repeat=delta)
            elif delta < 0:
                keys.send('UI_Up', hold=0.05, repeat=abs(delta))

            sleep(0.75)
            keys.send('UI_Select')  # Select that commodity

            if self.ap.debug_overlay:
                q = Quad.from_rect(self.parent.reg['sell_qty_box']['rect'])
                self.ap.overlay.overlay_quad_pct('sell_qty_box', q, (0, 255, 0), 2, 5)
                self.ap.overlay.overlay_paint()

            sleep(0.5)  # give time for popup
            keys.send('UI_Up', repeat=2)  # make sure at top

            # Set quantity
            if act_qty >= 9999 or qty_in_cargo <= act_qty:
                self.ap_ckb('log+vce', f"Selling all our units of {name}.")
                logger.info(f"Attempting to sell all our units of {name}")
                max_qty = qty_in_cargo
            else:
                self.ap_ckb('log+vce', f"Selling {act_qty} units of {name}.")
                logger.info(f"Attempting to sell {act_qty} units of {name}")
                max_qty = qty_in_cargo

            self._set_buy_sell_quantity(keys, min(act_qty, max_qty), max_qty)

            keys.send('UI_Down')  # Down to the Sell button
            self.ap.jn.ship['last_market_sell'] = None  # clear before sell so we detect the new event
            keys.send('UI_Select')  # Select to Sell

            # Cross-check with journal for actual quantity sold
            actual_qty = act_qty
            for _ in range(10):  # wait up to 2s for MarketSell event
                sleep(0.2)
                ship = self.ap.jn.ship_state()
                last_sell = ship.get('last_market_sell')
                if last_sell and last_sell['Type'].upper() == name.upper():
                    actual_qty = last_sell['Count']
                    if actual_qty != act_qty:
                        logger.warning(f"Sell {name}: journal says {actual_qty}, planned {act_qty}")
                        self.ap_ckb('log', f"Sell mismatch: got {actual_qty}/{act_qty} {name}")
                    break

            # After selling all, item may disappear from list
            sell_all = (actual_qty >= qty_in_cargo)
            if sell_all:
                pass  # cursor stays at same index (next item slid up)
            else:
                self._cursor_pos = index

        return True, actual_qty

    def capture_goods_panel(self):
        """ Get the location panel from within the nav panel.
        Returns an image, or None.
        """
        # Scale the regions based on the target resolution.
        region = self.parent.reg['commodity_column']
        img = self.ocr.capture_region_pct(region)
        if img is None:
            return False

        if self.ap.debug_overlay:
            # Offset to match the nav panel offset
            q = Quad.from_rect(self.parent.reg['commodity_column']['rect'])
            self.ap.overlay.overlay_quad_pix('capture_goods_panel', q, (0, 255, 0), 2, 5)
            self.ap.overlay.overlay_paint()

        return img


def dummy_cb(msg, body=None):
    pass


# Usage Example
if __name__ == "__main__":
    from src.autopilot.ED_AP import EDAutopilot
    test_ed_ap = EDAutopilot(cb=dummy_cb)
    test_ed_ap.keys.activate_window = True
    svcs = EDStationServicesInShip(test_ed_ap, test_ed_ap.scr, test_ed_ap.keys, test_ed_ap.ap_ckb)
    #svcs.goto_station_services()
    #svcs.goto_commodities_market()

    while 1:
        load_calibrated_regions('EDStationServicesInShip', svcs.reg)

        for key, value in svcs.reg.items():
            commodities_market = Quad.from_rect(svcs.reg[key]['rect'])
            test_ed_ap.overlay.overlay_quad_pct(key, commodities_market, (0, 255, 0), 2, 7)

        # commodities_market = Quad.from_rect(svcs.reg['commodities_market']['rect'])
        # test_ed_ap.overlay.overlay_quad_pct('commodities_market', commodities_market, (0, 255, 0), 2, 7)
        #
        # commodity_column = Quad.from_rect(svcs.reg['commodity_column']['rect'])
        # test_ed_ap.overlay.overlay_quad_pct('commodity_column', commodity_column, (0, 255, 0), 2, 7)
        #
        # buy_qty_box = Quad.from_rect(svcs.reg['buy_qty_box']['rect'])
        # test_ed_ap.overlay.overlay_quad_pct('buy_qty_box', buy_qty_box, (0, 255, 0), 2, 7)

        test_ed_ap.overlay.overlay_paint()

        sleep(0.5)


