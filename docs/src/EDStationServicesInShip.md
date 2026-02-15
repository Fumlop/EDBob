# EDStationServicesInShip.py

## Purpose
Handles station services interfaces accessed from a docked ship. Manages navigation to commodities market, passenger lounge, and construction services. Executes buying/selling of commodities at different station types with layout detection.

## Key Classes/Functions
- EDStationServicesInShip: Main class for station services navigation
- PassengerLounge: Sub-class for passenger mission operations (placeholder)
- CommoditiesMarket: Sub-class for buy/sell commodity operations

## Key Methods
- goto_station_services(): Navigates to station services menu
- goto_construction_services(): Navigates to orbital construction site services
- determine_commodities_location(): Detects station type and returns menu navigation pattern (RRD, RD, R, D)
- goto_commodities_market(): Navigates to commodities market based on station type
- select_buy() / select_sell(): Selects buy or sell mode in commodities market
- buy_commodity(keys, name, qty, free_cargo): Purchases commodity with cargo limit checking
- sell_commodity(keys, name, qty, cargo_parser): Sells commodity from cargo
- sell_to_colonisation_ship(ap): Sells all cargo to colony ship

## Dependencies
- MarketParser: Market data reading
- StatusParser: Game status checking
- Screen_Regions: Region management and calibration
- cv2: Image operations

## Notes
- Station layout varies by type (Fleet Carrier, Squadron, Outpost, Orbital)
- Uses StationType enum to determine menu navigation
- Calibrated regions support different screen resolutions
- Buy operations check available stock and cargo space
- Sell operations use market data and player cargo inventory
