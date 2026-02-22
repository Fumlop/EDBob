# MarketParser.py -- Market.json Parser

## Purpose

Parses the Elite Dangerous `Market.json` file to read station commodity market data. Provides buyable/sellable item filtering, individual item lookup, and availability checks.
Lives in `src/ed/MarketParser.py`.

## Class: MarketParser

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `file_path` | str or None | Custom path to Market.json. Auto-detects on Windows (SavedGames) and Linux (`./linux_ed/`). |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `file_path` | str | Absolute path to Market.json |
| `last_mod_time` | float or None | Last known file modification timestamp |
| `current_data` | dict or None | Latest parsed market data |

### Market Item Format

```json
{
  "id": 128049154,
  "Name": "$gold_name;",
  "Name_Localised": "Gold",
  "Category": "$MARKET_category_metals;",
  "Category_Localised": "Metals",
  "BuyPrice": 49118, "SellPrice": 48558, "MeanPrice": 47609,
  "StockBracket": 2, "DemandBracket": 0,
  "Stock": 89, "Demand": 1,
  "Consumer": true, "Producer": true, "Rare": false
}
```

### Methods

| Method | Returns | Description |
|---|---|---|
| `get_file_modified_time()` | float | Returns OS file modification timestamp. |
| `get_market_data()` | dict or None | Read Market.json if modified, return parsed data. Returns None if file does not exist. Uses exponential backoff (1s start, 2x) on read failure. |
| `get_sellable_items(cargo_parser)` | list or None | Get items that can be sold to station. Filters by `Consumer` flag, or demand > 0 / Rare with cargo in hold. Sorted by name then category. Triggers file re-read. |
| `get_buyable_items()` | list or None | Get items that can be bought from station. Filters via `can_buy_item()`. Sorted by name then category. Triggers file re-read. |
| `get_market_name()` | str | Returns current station name. Does NOT trigger file re-read. Returns empty string if no data. |
| `get_item(item_name)` | dict or None | Get details of one item by `Name_Localised` (case-insensitive). Does NOT trigger file re-read. |
| `can_buy_item(item_name)` | bool | Check if item is purchasable: (`Stock > 0` and `Producer` and not `Rare`) or (`Stock > 0` and `Rare`). Does NOT trigger file re-read. |
| `can_sell_item(item_name)` | bool | Check if item is sellable: `Consumer` or `Demand > 0` or `Rare`. Does NOT trigger file re-read. |

### Bracket Values

| Bracket | StockBracket | DemandBracket |
|---|---|---|
| 0 | Not listed | Not listed |
| 1 | Low Stock | Low Demand |
| 2 | Medium Stock | Medium Demand |
| 3 | High Stock | High Demand |

## Dependencies

| Module | Purpose |
|---|---|
| `EDlogger` | Logging |
| `WindowsKnownPaths` | SavedGames path resolution (Windows, imported conditionally) |

## Notes

- Sellable items filtering uses `cargo_parser` parameter to check if rare/demand=1 items exist in hold
- Buyable/sellable lists are sorted by `Name_Localised` then `Category_Localised` (matches in-game market order)
- File change detection uses OS modification time (fast path)
- Read retry uses exponential backoff starting at 1s
- Handles both Windows and Linux paths
- `current_data` can be modified externally (e.g. `CommoditiesMarket` sets `StockBracket=0` after buying all stock)
