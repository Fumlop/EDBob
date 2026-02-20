from __future__ import annotations

import os
from time import sleep
from src.ed.CargoParser import CargoParser
from src.core import EDAP_data
from src.core.EDAP_data import FlagsDocked, FlagsLanded
from src.ed.EDJournal import StationType
from src.ed.EDKeys import EDKeys
from src.core.EDlogger import logger
import json
from src.ed.MarketParser import MarketParser
from src.core.MousePt import MousePoint
from pathlib import Path

"""
File: EDWayPoint.py    

Description:
   Class will load file called waypoints.json which contains a list of System name to jump to.
   Provides methods to select a waypoint pass into it.  

Author: sumzer0@yahoo.com
"""


class EDWayPoint:
    def __init__(self, ed_ap, is_odyssey=True):
        self.ap = ed_ap
        # self.is_odyssey = is_odyssey
        self.filename = ''
        self.stats_log = {'Colonisation': 0, 'Construction': 0, 'Fleet Carrier': 0, 'Station': 0}
        self.waypoints = {}
        self.num_waypoints = 0
        self.step = 0
        self._last_bookmark_set = None
        self.market_parser = MarketParser()
        self.cargo_parser = CargoParser()

    @property
    def _waypoint_path(self):
        """Path to the current waypoint file."""
        return './waypoints/' + Path(self.filename).name

    def load_waypoint_file(self, filename='./waypoints/waypoints.json') -> bool:
        if not os.path.exists(filename):
            return False

        ss = self._read_waypoints(filename)

        if ss is not None:
            self.waypoints = ss
            self.num_waypoints = len(self.waypoints)
            self.filename = filename
            self.ap.config['WaypointFilepath'] = filename
            self.ap.ap_ckb('log', f"Loaded Waypoint file: {filename}")
            logger.debug("EDWayPoint: read json:" + str(ss))
            return True

        self.ap.ap_ckb('log', f"Waypoint file is invalid. Check log file for details.")
        return False

    def _read_waypoints(self, filename='./waypoints/waypoints.json'):
        if not os.path.exists(filename):
            return None

        s = None
        self.ap.config['WaypointFilepath'] = filename
        try:
            with open(filename, "r") as fp:
                s = json.load(fp)

            # Perform any checks on the data returned
            # Check if the waypoint data contains the 'GlobalShoppingList' (new requirement)
            if 'GlobalShoppingList' not in s:
                # self.ap.ap_ckb('log', f"Waypoint file is invalid. Check log file for details.")
                logger.warning(f"Waypoint file {filename} is invalid or old version. "
                               f"It does not contain a 'GlobalShoppingList' waypoint.")
                s = None

            # Validate required fields per entry type (skip if already invalid)
            _GLOBAL_FIELDS = {'BuyCommodities', 'UpdateCommodityCount', 'Skip'}
            _WAYPOINT_FIELDS = {
                'SystemName', 'StationName', 'GalaxyBookmarkType', 'GalaxyBookmarkNumber',
                'SystemBookmarkType', 'SystemBookmarkNumber', 'SellCommodities',
                'BuyCommodities', 'UpdateCommodityCount', 'FleetCarrierTransfer',
                'Skip', 'Completed',
            }

            err = False
            for key, value in (s or {}).items():
                required = _GLOBAL_FIELDS if key == 'GlobalShoppingList' else _WAYPOINT_FIELDS
                for field in required:
                    if field not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain '{field}'.")
                        err = True

            if err:
                s = None

        except Exception as e:
            logger.warning("EDWayPoint.py read_waypoints error :" + str(e))

        return s

    def write_waypoints(self, data, filename='./waypoints/waypoints.json'):
        if data is None:
            data = self.waypoints
        try:
            self.ap.config['WaypointFilepath'] = filename
            with open(filename, "w") as fp:
                json.dump(data, fp, indent=4)
        except Exception as e:
            logger.warning("EDWayPoint.py write_waypoints error:" + str(e))

    def mark_waypoint_complete(self, key):
        self.waypoints[key]['Completed'] = True
        self.write_waypoints(data=None, filename=self._waypoint_path)

    def get_waypoint(self) -> tuple[str, dict] | tuple[None, None]:
        """ Returns the next waypoint list or None if we are at the end of the waypoints.
        """
        dest_key = "-1"

        # loop back to beginning if last record is "REPEAT"
        while dest_key == "-1":
            for i, key in enumerate(self.waypoints):
                # skip records we already processed
                if i < self.step:
                    continue

                # if this entry is REPEAT (and not skipped), mark them all as Completed = False
                if ((self.waypoints[key].get('SystemName', "").upper() == "REPEAT")
                        and not self.waypoints[key]['Skip']):
                    self.mark_all_waypoints_not_complete()
                    break

                # if this step is marked to skip... i.e. completed, go to next step
                if (key == "GlobalShoppingList" or self.waypoints[key]['Completed']
                        or self.waypoints[key]['Skip']):
                    continue

                # This is the next uncompleted step
                self.step = i
                dest_key = key
                break
            else:
                return None, None

        return dest_key, self.waypoints[dest_key]

    def mark_all_waypoints_not_complete(self):
        for j, tkey in enumerate(self.waypoints):
            # Ensure 'Completed' key exists before trying to set it
            if 'Completed' in self.waypoints[tkey]:
                self.waypoints[tkey]['Completed'] = False
            else:
                # Handle legacy format where 'Completed' might be missing
                # Or log a warning if the structure is unexpected
                logger.warning(f"Waypoint {tkey} missing 'Completed' key during reset.")
            self.step = 0
        self.write_waypoints(data=None, filename=self._waypoint_path)
        self.log_stats()

    def log_stats(self):
        calc1 = 1.5 ** self.stats_log['Colonisation']
        calc2 = 1.5 ** self.stats_log['Construction']
        sleep(max(calc1, calc2))

    def _sync_from_construction_depot(self):
        """Sync waypoint commodity counts from the latest ColonisationConstructionDepot journal event.
        Updates GlobalShoppingList and buy waypoints to reflect what's still needed.
        """
        depot = self.ap.jn.ship_state().get('ConstructionDepotDetails')
        if not depot or not isinstance(depot, dict):
            return
        resources = depot.get('ResourcesRequired')
        if not resources or not isinstance(resources, list):
            return

        # Build remaining needs: {commodity_name: remaining_qty}
        remaining = {}
        for item in resources:
            need = item['RequiredAmount'] - item['ProvidedAmount']
            if need > 0:
                remaining[item['Name_Localised']] = need

        if not remaining:
            logger.info("Construction depot: all resources fully provided")
            return

        # Update GlobalShoppingList
        gsl = self.waypoints.get('GlobalShoppingList', {}).get('BuyCommodities', {})
        updated = False
        for commodity in list(gsl.keys()):
            if commodity in remaining:
                if gsl[commodity] != remaining[commodity]:
                    logger.info(f"Sync GlobalShoppingList: {commodity} {gsl[commodity]} -> {remaining[commodity]}")
                    gsl[commodity] = remaining[commodity]
                    updated = True

        # Update buy waypoints
        for key in self.waypoints:
            if key == "GlobalShoppingList":
                continue
            wp = self.waypoints[key]
            buy = wp.get('BuyCommodities', {})
            for commodity in list(buy.keys()):
                if commodity in remaining:
                    if buy[commodity] != remaining[commodity]:
                        logger.info(f"Sync waypoint #{key}: {commodity} {buy[commodity]} -> {remaining[commodity]}")
                        buy[commodity] = remaining[commodity]
                        updated = True

        if updated:
            self.write_waypoints(data=None, filename=self._waypoint_path)
            self.ap.ap_ckb('log', 'Synced commodity counts from construction depot')

    def _buy_one(self, ap, name, qty, cargo_capacity):
        """Buy one commodity, wait for status update. Returns (bought, full)."""
        curr_cargo_qty = int(ap.status.get_cleaned_data()['Cargo'])
        cargo_timestamp = ap.status.current_data['timestamp']

        free_cargo = cargo_capacity - curr_cargo_qty
        logger.info(f"Execute trade: Free cargo space: {free_cargo}")

        if free_cargo == 0:
            logger.info(f"Execute trade: No space for additional cargo")
            return 0, True

        logger.info(f"Execute trade: Shopping list requests {qty} units of {name}")
        result, bought = self.ap.stn_svcs_in_ship.commodities_market.buy_commodity(
            ap.keys, name, qty, free_cargo)
        logger.info(f"Execute trade: Bought {bought} units of {name}")

        if bought > 0:
            ap.status.wait_for_file_change(cargo_timestamp, 5)

        return bought, False

    def execute_trade(self, ap, dest_key):
        # Get trade commodities from waypoint
        sell_commodities = self.waypoints[dest_key]['SellCommodities']
        buy_commodities = self.waypoints[dest_key]['BuyCommodities']
        fleetcarrier_transfer = self.waypoints[dest_key]['FleetCarrierTransfer']
        global_buy_commodities = self.waypoints['GlobalShoppingList']['BuyCommodities']

        if len(sell_commodities) == 0 and len(buy_commodities) == 0 and len(global_buy_commodities) == 0:
            return 0

        # Does this place have commodities service?
        # From the journal, this works for stations (incl. outpost), colonisation ship and megaships
        if ap.jn.ship_state()['StationServices'] is not None:
            if 'commodities' not in ap.jn.ship_state()['StationServices']:
                self.ap.ap_ckb('log', f"No commodities market at docked location.")
                return 0
        else:
            self.ap.ap_ckb('log', f"No station services at docked location.")
            return 0

        total_bought = 0

        # Determine type of station we are at
        station_type = ap.jn.ship_state()['exp_station_type']

        if station_type == StationType.ColonisationShip or station_type == StationType.SpaceConstructionDepot:
            if station_type == StationType.ColonisationShip:
                # Colonisation Ship
                self.stats_log['Colonisation'] = self.stats_log['Colonisation'] + 1
                self.ap.ap_ckb('log', f"Executing trade with Colonisation Ship.")
                logger.debug(f"Execute Trade: On Colonisation Ship")
            if station_type == StationType.SpaceConstructionDepot:
                # Construction Ship
                self.stats_log['Construction'] = self.stats_log['Construction'] + 1
                self.ap.ap_ckb('log', f"Executing trade with Orbital Construction Ship.")
                logger.debug(f"Execute Trade: On Orbital Construction Site")

            # Go to station services
            self.ap.stn_svcs_in_ship.goto_construction_services()

            # --------- SELL ----------
            if len(sell_commodities) > 0:
                # Sell all to colonisation/construction ship
                self.sell_to_colonisation_ship(ap)

            return None  # delivery only, no buy attempted

        elif (station_type == StationType.FleetCarrier and fleetcarrier_transfer or
              station_type == StationType.SquadronCarrier and fleetcarrier_transfer):
            # Fleet Carrier in Transfer mode
            self.stats_log['Fleet Carrier'] = self.stats_log['Fleet Carrier'] + 1
            # --------- SELL ----------
            if len(sell_commodities) > 0:
                # Transfer to Fleet Carrier
                self.ap.internal_panel.transfer_to_fleetcarrier(ap)

            # --------- BUY ----------
            if len(buy_commodities) > 0:
                self.ap.internal_panel.transfer_from_fleetcarrier(ap, buy_commodities)

        else:
            # Regular Station or Fleet Carrier or Squadron Carrier in Buy/Sell mode
            self.ap.ap_ckb('log', "Executing trade.")
            logger.debug(f"Execute Trade: On Regular Station")
            self.stats_log['Station'] = self.stats_log['Station'] + 1

            market_time_old = ""
            data = self.market_parser.get_market_data()
            if data is not None:
                market_time_old = self.market_parser.current_data['timestamp']

            # Go to the Station Commodities Market
            self.ap.stn_svcs_in_ship.goto_commodities_market()
            self.ap.ap_ckb('log+vce', "Downloading commodities data from market.")

            # Wait for market to update
            market_time_new = ""
            data = self.market_parser.get_market_data()
            if data is not None:
                market_time_new = self.market_parser.current_data['timestamp']

            while market_time_new == market_time_old:
                market_time_new = ""
                data = self.market_parser.get_market_data()
                if data is not None:
                    market_time_new = self.market_parser.current_data['timestamp']
                sleep(1)  # wait for new menu to finish rendering

            cargo_capacity = ap.jn.ship_state()['cargo_capacity']
            logger.info(f"Execute trade: Ship's max cargo capacity: {cargo_capacity}")

            # --------- SELL ----------
            if len(sell_commodities) > 0:
                # Select the SELL option
                self.ap.stn_svcs_in_ship.commodities_market.select_sell(ap.keys)

                for i, key in enumerate(sell_commodities):
                    # Check if we have any of the item to sell
                    self.cargo_parser.get_cargo_data()
                    cargo_parser_timestamp = self.cargo_parser.current_data['timestamp']

                    # Check if we want to sell ALL commodities
                    if key == "ALL":
                        for cargo_item in self.cargo_parser.get_items():
                            name = cargo_item.get('Name')
                            name_loc = cargo_item.get('Name_Localised', name)

                            # Sell all we have of the commodity
                            result, qty = self.ap.stn_svcs_in_ship.commodities_market.sell_commodity(ap.keys, name_loc, sell_commodities[key], self.cargo_parser)

                            # If we sold any goods, wait for cargo parser file to update with cargo available to sell
                            if qty > 0:
                                self.cargo_parser.wait_for_file_change(cargo_parser_timestamp, 5)

                                # Check if we have any of the item to sell
                                self.cargo_parser.get_cargo_data()
                                cargo_parser_timestamp = self.cargo_parser.current_data['timestamp']
                    else:
                        cargo_item = self.cargo_parser.get_item(key)
                        if cargo_item is None:
                            logger.info(f"Unable to sell {key}. None in cargo hold.")
                            continue

                        # Sell the commodity
                        result, qty = self.ap.stn_svcs_in_ship.commodities_market.sell_commodity(ap.keys, key, sell_commodities[key], self.cargo_parser)

                        # Update counts if necessary
                        if qty > 0 and self.waypoints[dest_key]['UpdateCommodityCount']:
                            sell_commodities[key] = sell_commodities[key] - qty

                # Save changes
                self.write_waypoints(data=None, filename=self._waypoint_path)

            sleep(1)

            # --------- BUY ----------
            if len(buy_commodities) > 0 or len(global_buy_commodities) > 0:
                # Select the BUY option
                self.ap.stn_svcs_in_ship.commodities_market.select_buy(ap.keys)

                # Go through buy commodities list (lowest quantity first to fit all)
                for key in sorted(buy_commodities, key=lambda k: buy_commodities[k]):
                    if key == "ALL":
                        buyable_items = self.market_parser.get_buyable_items()
                        if buyable_items is not None:
                            for value in buyable_items:
                                bought, full = self._buy_one(ap, value['Name_Localised'], buy_commodities[key], cargo_capacity)
                                total_bought += bought
                                if full:
                                    break
                    else:
                        bought, full = self._buy_one(ap, key, buy_commodities[key], cargo_capacity)
                        total_bought += bought
                        if bought > 0 and self.waypoints[dest_key]['UpdateCommodityCount']:
                            buy_commodities[key] -= bought
                        if full:
                            break

                # Go through global buy commodities list (lowest quantity first)
                for key in sorted(global_buy_commodities, key=lambda k: global_buy_commodities[k]):
                    bought, full = self._buy_one(ap, key, global_buy_commodities[key], cargo_capacity)
                    total_bought += bought
                    if bought > 0 and self.waypoints['GlobalShoppingList']['UpdateCommodityCount']:
                        global_buy_commodities[key] -= bought
                    if full:
                        break

                # Save changes
                self.write_waypoints(data=None, filename=self._waypoint_path)

            sleep(1.5)  # give time to popdown
            # Go to ship view
            ap.ship_control.goto_cockpit_view()

        return total_bought

    def waypoint_assist(self, keys, scr_reg):
        """ Processes the waypoints, performing jumps and sc assist if going to a station
        also can then perform trades if specific in the waypoints file.
        """
        if len(self.waypoints) == 0:
            self.ap.ap_ckb('log+vce', "No Waypoint file loaded. Exiting Waypoint Assist.")
            return

        self.step = 0  # start at first waypoint
        self.mark_all_waypoints_not_complete()  # reset completed flags on each start
        self.ap.ap_ckb('log', "Waypoint file: " + str(Path(self.filename).name))
        self.reset_stats()

        # Auto-detect starting waypoint: if docked at a waypoint station, start there
        cur_station = (self.ap.jn.ship_state()['cur_station'] or '').upper()
        cur_station_type = self.ap.jn.ship_state()['exp_station_type']
        is_docked = self.ap.status.get_flag(FlagsDocked)
        if is_docked and cur_station != "":
            for i, key in enumerate(self.waypoints):
                if key == "GlobalShoppingList":
                    continue
                wp = self.waypoints[key]
                wp_station = wp.get('StationName', '').upper()
                if wp_station == "" or wp.get('SystemName', '').upper() == "REPEAT":
                    continue
                # Match: exact name, or colonisation/construction partial match
                matched = False
                if wp_station == cur_station:
                    matched = True
                elif ('COLONISATION SHIP' in wp_station or 'CONSTRUCTION' in wp_station):
                    if (cur_station_type == StationType.ColonisationShip or
                            cur_station_type == StationType.SpaceConstructionDepot):
                        matched = True
                if matched:
                    self.step = i
                    logger.info(f"Auto-detected start at waypoint #{key}: {wp_station} (docked at {cur_station})")
                    self.ap.ap_ckb('log', f"Starting at waypoint #{key} (already docked)")
                    break

        # Sync commodity counts from construction depot journal data
        self._sync_from_construction_depot()

        # Loop until complete, or error
        _abort = False
        while not _abort:
            self.ap.check_stop()

            # Current location
            cur_star_system = self.ap.jn.ship_state()['cur_star_system'].upper()
            cur_station = (self.ap.jn.ship_state()['cur_station'] or '').upper()

            # ====================================
            # Get next Waypoint
            # ====================================
            old_step = self.step
            dest_key, next_waypoint = self.get_waypoint()

            if dest_key is None:
                self.ap.ap_ckb('log+vce', "Waypoint list has been completed.")
                break

            if self.step != old_step:
                self._last_bookmark_set = None

            gal_bookmark_type = next_waypoint.get('GalaxyBookmarkType', '')
            gal_bookmark_num = next_waypoint.get('GalaxyBookmarkNumber', 0)
            next_wp_station = next_waypoint.get('StationName', '').upper()

            if gal_bookmark_num <= 0:
                self.ap.ap_ckb('log+vce', f"Waypoint {dest_key} has no galaxy bookmark. Aborting.")
                _abort = True
                break

            # ====================================
            # If Docked -- trade, then get next target and undock
            # ====================================
            if self.ap.status.get_flag(FlagsDocked):
                # Check if construction already complete (only at construction waypoints)
                if 'construction' in next_wp_station.lower():
                    depot = self.ap.jn.ship_state().get('ConstructionDepotDetails')
                    if isinstance(depot, dict) and depot.get('ConstructionComplete', False):
                        self.ap.ap_ckb('log+vce', "Construction complete! Stopping waypoint assist.")
                        break

                self.ap.check_stop()
                self.ap.ap_ckb('log+vce', f"Execute trade at: {cur_station}")
                total_bought = self.execute_trade(self.ap, dest_key)
                if total_bought is not None and total_bought == 0:
                    buy_list = self.waypoints[dest_key].get('BuyCommodities', {})
                    global_list = self.waypoints.get('GlobalShoppingList', {}).get('BuyCommodities', {})
                    wanted = sum(v for v in buy_list.values() if isinstance(v, (int, float)) and v > 0)
                    wanted += sum(v for v in global_list.values() if isinstance(v, (int, float)) and v > 0)
                    has_list = len(buy_list) > 0 or len(global_list) > 0
                    if wanted > 0:
                        self.ap.ap_ckb('log+vce', "Nothing available to buy -- stopping for reconfiguration.")
                        break
                    elif has_list and wanted == 0:
                        self.ap.ap_ckb('log+vce', "All commodities fulfilled (counts at 0) -- stopping.")
                        break
                self.mark_waypoint_complete(dest_key)
                self.ap.ap_ckb('log+vce', f"Waypoint complete.")

                # Check again after trade (may have just delivered final batch)
                if 'construction' in next_wp_station.lower():
                    depot = self.ap.jn.ship_state().get('ConstructionDepotDetails')
                    if isinstance(depot, dict) and depot.get('ConstructionComplete', False):
                        self.ap.ap_ckb('log+vce', "Construction complete! Stopping waypoint assist.")
                        break

                # Get NEXT waypoint for navigation
                dest_key, next_waypoint = self.get_waypoint()
                if dest_key is None:
                    self.ap.ap_ckb('log+vce', "Waypoint list has been completed.")
                    break

                gal_bookmark_type = next_waypoint.get('GalaxyBookmarkType', '')
                gal_bookmark_num = next_waypoint.get('GalaxyBookmarkNumber', 0)
                next_wp_station = next_waypoint.get('StationName', '').upper()

                if gal_bookmark_num <= 0:
                    self.ap.ap_ckb('log+vce', f"Waypoint {dest_key} has no galaxy bookmark. Aborting.")
                    _abort = True
                    break

                # Set bookmark and undock before falling through to navigation
                self.ap.check_stop()
                self.ap.ap_ckb('log+vce', f"Next target: favorite #{gal_bookmark_num}")
                res = self.ap.galaxy_map.set_gal_map_dest_bookmark(self.ap, gal_bookmark_type, gal_bookmark_num)
                if not res:
                    self.ap.ap_ckb('log+vce', f"Unable to set Galaxy Map bookmark.")
                    _abort = True
                    break
                self._last_bookmark_set = (gal_bookmark_type, gal_bookmark_num)
                sleep(1)

                self.ap.check_stop()
                self.ap.waypoint_undock_seq()
                # Fall through to navigation

            # ====================================
            # Navigation (single path for all states)
            # ====================================
            if self._last_bookmark_set != (gal_bookmark_type, gal_bookmark_num):
                self.ap.ap_ckb('log+vce', f"Targeting favorite #{gal_bookmark_num}")
                res = self.ap.galaxy_map.set_gal_map_dest_bookmark(self.ap, gal_bookmark_type, gal_bookmark_num)
                if not res:
                    self.ap.ap_ckb('log+vce', f"Unable to set Galaxy Map bookmark.")
                    _abort = True
                    break
                self._last_bookmark_set = (gal_bookmark_type, gal_bookmark_num)
                sleep(1)

            self.ap.check_stop()
            # Different system? Jump there
            cur_star_system = self.ap.jn.ship_state()['cur_star_system'].upper()
            nav_dest = self.ap.nav_route.get_last_system().upper()
            if nav_dest != "" and nav_dest != cur_star_system:
                self.ap.sc_engage()
                keys.send('TargetNextRouteSystem')
                self.ap.ap_ckb('log+vce', f"Jumping to {nav_dest}.")
                self.ap.do_route_jump(scr_reg)
                continue

            # Same system -- SC to station (blocks until docked or failed)
            sc_target = next_wp_station
            if sc_target == "":
                sc_target = self.ap.status.get_cleaned_data().get('Destination_Name', '')
            if sc_target != "":
                self.ap.supercruise_to_station(scr_reg, sc_target)
                sleep(1)
                continue

            # No target found -- reset
            logger.warning("Not docked and no target. Resetting to waypoint #1.")
            self.ap.ap_ckb('log+vce', "No target found. Resetting to waypoint #1.")
            self.mark_all_waypoints_not_complete()
            self._last_bookmark_set = None
            continue

        # Done with waypoints
        if not _abort:
            self.ap.ap_ckb('log+vce',
                           "Waypoint Route Complete, total distance jumped: " + str(self.ap.total_dist_jumped) + "LY")
            self.ap.update_ap_status("Idle")
        else:
            self.ap.ap_ckb('log+vce', "Waypoint Route was aborted.")
            self.ap.update_ap_status("Idle")

    def reset_stats(self):
        # Clear stats
        self.stats_log['Colonisation'] = 0
        self.stats_log['Construction'] = 0
        self.stats_log['Fleet Carrier'] = 0
        self.stats_log['Station'] = 0

    def sell_to_colonisation_ship(self, ap):
        self.ap.stn_svcs_in_ship.sell_to_colonisation_ship(self.ap)


def main():
    from src.autopilot.ED_AP import EDAutopilot

    ed_ap = EDAutopilot(cb=None)
    wp = EDWayPoint(ed_ap, True)  # False = Horizons
    wp.step = 0  # start at first waypoint
    keys = EDKeys(cb=None)
    keys.activate_window = True
    wp.ap.stn_svcs_in_ship.commodities_market.select_sell(keys)


if __name__ == "__main__":
    main()
