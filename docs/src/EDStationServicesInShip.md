# EDStationServicesInShip.py -- Station Services & Commodity Trading

## Purpose

Handles docked station interactions: navigating to station services, commodities market, buying/selling commodities, and colonisation ship transfers. Contains three classes: the main `EDStationServicesInShip` coordinator, `PassengerLounge` (layout data only), and `CommoditiesMarket` (buy/sell logic).
Lives in `src/ed/EDStationServicesInShip.py`.

## Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `dummy_cb(msg, body=None)` | None | No-op callback for standalone testing |

## Class: EDStationServicesInShip

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance |
| `screen` | Screen | Screen capture instance |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `ap` | EDAutopilot | Parent reference |
| `ocr` | OCR | OCR instance |
| `locale` | dict | Localized strings |
| `passenger_lounge` | PassengerLounge | Passenger lounge sub-handler |
| `commodities_market` | CommoditiesMarket | Market buy/sell sub-handler |
| `status_parser` | StatusParser | Status.json reader |
| `market_parser` | MarketParser | Market.json reader |
| `reg` | dict | Screen regions (loaded from calibration) |

### Screen Regions

| Key | Description |
|---|---|
| `commodities_market` | Market area |
| `station_services` | Full services panel |
| `connected_to` | Station name header |
| `title` | Page title |
| `commodity_column` | Commodity list column |
| `buy_qty_box` | Buy quantity input box |
| `sell_qty_box` | Sell quantity input box |
| `commodity_name` | Commodity name area |

### Methods

| Method | Returns | Description |
|---|---|---|
| `goto_station_services()` | bool | Delegates to `MenuNav.open_station_services()`. Shows debug overlay on success. |
| `goto_construction_services()` | bool | Navigates to construction services for Orbital Construction Sites. Uses `goto_cockpit` + `realign_cursor` + manual key sequence. Waits 3s for menu render. |
| `determine_commodities_location()` | str | Returns navigation path to commodities button based on station type: `"RR"` (FleetCarrier), `"RD"` (SquadronCarrier), `"R"` (Outpost), `"D"` (Orbital). |
| `goto_commodities_market()` | bool | Navigates from docked menu to commodities market using path from `determine_commodities_location()`. Waits 5s for station services render, 2s for market transition. |
| `sell_to_colonisation_ship(ap)` | None | Static method. Delegates to `MenuNav.transfer_all_to_colonisation()`. |

### Station Type to Commodities Path

| Station Type | Path | UI Keys |
|---|---|---|
| FleetCarrier | `"RR"` | Right x2, Select |
| SquadronCarrier | `"RD"` | Right, Down, Select |
| Outpost | `"R"` | Right, Select |
| Orbital (default) | `"D"` | Down, Select |

## Class: PassengerLounge

Layout data holder for passenger lounge UI regions. No active methods.

### Attributes

| Attribute | Description |
|---|---|
| `reg` | Screen regions: `no_cmpl_missions`, `mission_dest_col`, `complete_mission_col` |
| `*_row_width` / `*_row_height` | Row dimensions in pixels at 1920x1080 |

## Class: CommoditiesMarket

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `station_services_in_ship` | EDStationServicesInShip | Parent reference |
| `ed_ap` | EDAutopilot | Autopilot instance |
| `ocr` | OCR | OCR instance |
| `keys` | EDKeys | Key sender |
| `screen` | Screen | Screen capture |
| `cb` | callable | GUI callback |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `market_parser` | MarketParser | Market.json reader |
| `reg` | dict | Regions: `cargo_col`, `commodity_name_col`, `supply_demand_col` |
| `commodity_row_width` | int | 422 px at 1920x1080 |
| `commodity_row_height` | int | 35 px at 1920x1080 |
| `_cursor_pos` | int | Current row position in commodity list |

### Methods

| Method | Returns | Description |
|---|---|---|
| `_ocr_quantity()` | int | Read buy/sell quantity from screen via OCR. Returns current value or -1 on failure. Uses orange + white HSV masks on cropped quantity box. |
| `_set_buy_sell_quantity(keys, target_qty, max_qty, sell=False)` | None | Set buy/sell quantity in popup. For buy: hold `UI_Right` 4s if max, else repeat tap. For sell: quantity is prefilled (no action if max). |
| `select_buy(keys)` | bool | Navigate to Buy tab on commodities screen. Resets `_cursor_pos` to 0. |
| `select_sell(keys)` | bool | Navigate to Sell tab on commodities screen. Resets `_cursor_pos` to 0. |
| `buy_commodity(keys, name, qty, free_cargo)` | (bool, int) | Buy commodity by name. Checks market availability, navigates from `_cursor_pos` to target index, sets quantity, confirms. Cross-checks with journal `MarketBuy` event. Returns (success, actual_qty). |
| `sell_commodity(keys, name, qty, cargo_parser)` | (bool, int) | Sell commodity by name. Checks market demand, navigates to target, sells all (quantity prefilled). Cross-checks with journal `MarketSell` event. Returns (success, actual_qty). |
| `capture_goods_panel()` | image or False | Capture commodity column region for OCR. Shows debug overlay if enabled. |

### Buy/Sell Algorithm

1. Check market data via `MarketParser` for availability/demand
2. Find item index in sorted buyable/sellable list
3. Navigate from `_cursor_pos` using `UI_Down`/`UI_Up` delta
4. Select commodity, set quantity, confirm
5. Cross-check with journal event (up to 2s wait)
6. Track cursor position for next operation

## Dependencies

| Module | Purpose |
|---|---|
| `MenuNav` | `open_station_services`, `goto_cockpit`, `realign_cursor`, `transfer_all_to_colonisation` |
| `MarketParser` | Market.json data for buy/sell availability |
| `StatusParser` | GUI focus detection (`GuiFocusStationServices`) |
| `EDJournal` | `StationType` enum for station detection |
| `Screen_Regions` | `Quad`, `scale_region`, `load_calibrated_regions` |
| `cv2` | Image processing for OCR |

## Notes

- Cursor position tracking (`_cursor_pos`) avoids re-scrolling from top on each buy/sell
- When buying all stock, item disappears from list and cursor stays at same index
- Sell always sells all units (quantity prefilled by game)
- Journal cross-check detects mismatches between planned and actual quantities
- OCR quantity reading uses `easyocr` (optional import, returns -1 if unavailable)
