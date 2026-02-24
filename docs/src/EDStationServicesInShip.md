# src/ed/EDStationServicesInShip.py (423 lines)

Station services menu automation: refueling, repairs, commodity trading.

## Classes

### EDStationServicesInShip

Main station services navigator. Opens menus, selects services.

### PassengerLounge

Passenger mission management automation.

### CommoditiesMarket

Buy/sell commodities automation. Uses `MarketParser` for price data
and `EDJournal.set_field()` to track last buy/sell actions.

## Dependencies

- `src.ed.MarketParser` -- market price reading
- `src.ed.MenuNav` -- menu navigation
- `src.ed.StatusParser` -- state verification
- `src.ed.EDJournal` -- set_field for last_market_buy/sell tracking
