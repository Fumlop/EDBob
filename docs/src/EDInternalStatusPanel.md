# EDInternalStatusPanel.py

## Purpose
Manages the internal (right-hand) ship status panel in Elite Dangerous. Handles navigation between tabs (Modules, Fire Groups, Ship, Inventory, Storage, Status), captures and processes panel images, and executes cargo transfer operations with the Fleet Carrier.

## Key Classes/Functions
- EDInternalStatusPanel: Main class for internal panel control and image capture
- PassengerLounge: Sub-class for passenger lounge operations
- CommoditiesMarket: Sub-class for commodities market buy/sell operations

## Key Methods
- capture_panel_straightened(): Captures and deskews the panel image using perspective transformation
- show_panel(): Opens the internal panel if not already visible
- is_panel_active(): Determines if panel is open and identifies active tab via OCR
- show_inventory_tab(): Navigates to inventory tab
- transfer_to_fleetcarrier(ap): Transfers all cargo to Fleet Carrier
- transfer_from_fleetcarrier(ap, buy_commodities): Transfers specific commodities from Fleet Carrier
- buy_commodity(keys, name, qty, free_cargo): Buys commodity from market
- sell_commodity(keys, name, qty, cargo_parser): Sells commodity to market

## Dependencies
- cv2: Image processing
- Screen, Screen_Regions: Screen capture and region management
- StatusParser: Game status monitoring
- MarketParser: Market data parsing
- OCR: Text recognition on panel items
- EDNavigationPanel: Perspective transformation utilities

## Notes
- Uses perspective transformation to deskew skewed panel images
- OCR-based tab detection with multi-attempt retry logic
- Calibrated regions loaded from external configuration
- Supports both buying and selling with quantity limits based on cargo space
