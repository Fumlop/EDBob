# EDAPGui - Elite Dangerous Autopilot

Automated waypoint autopilot for Elite Dangerous. Flies trade routes, buys and sells commodities, docks at stations and fleet carriers -- all hands-off using screen capture and galaxy map bookmarks.

**Version:** V1.9.0 b4

---

## Requirements

| Requirement | Detail |
|---|---|
| OS | Windows 10 / 11 only |
| Python | 3.11+ |
| Resolution | **1920 x 1080** |
| Display mode | **Borderless Windowed** |
| HUD color | **Default orange** -- custom HUD colors are NOT supported |
| Docking computer | Required (autopilot requests docking, the game handles landing) |

Keybindings are auto-detected from your Elite Dangerous config files. No manual key setup needed.

---

## Install and Run

1. Double-click **`start_ed_ap.bat`**
2. First run creates a virtual environment and installs dependencies (takes a few minutes)
3. Every subsequent run launches the GUI directly

Alternative: run `install_requirements.bat` first, then `start_ed_ap.bat`.

---

## Quick Start

1. In Elite Dangerous, set **galaxy map bookmarks** for the systems you want to visit
2. Create a waypoint JSON file in the `waypoints/` folder (see below)
3. Start EDAPGui
4. Go to the **Waypoints** tab, click **Open**, load your file
5. Go to the **Main** tab, enable **Waypoint Assist**
6. The autopilot takes over -- it jumps, navigates, docks, trades, and loops

**To stop:** press the **End** key or uncheck Waypoint Assist. The autopilot finishes the current action and stops.

### Default Hotkeys

| Key | Action |
|---|---|
| Home | Start FSD Assist (jump between systems) |
| Insert | Start SC Assist (supercruise to station) |
| End | Stop all assists |

---

## Waypoint JSON Files

Waypoint files live in `waypoints/`. They define a route: where to go, what to buy, what to sell.

### Minimal Example -- Buy and Deliver

This route buys Aluminium at bookmark Favorites #2, sells everything at bookmark Favorites #3 (a construction site), then loops.

```json
{
    "GlobalShoppingList": {
        "BuyCommodities": { "Aluminium": 5000 },
        "UpdateCommodityCount": true,
        "FleetCarrierTransfer": false,
        "Skip": false,
        "Completed": false
    },
    "1": {
        "SystemName": "",
        "StationName": "",
        "GalaxyBookmarkType": "Favorites",
        "GalaxyBookmarkNumber": 2,
        "SystemBookmarkType": "Station",
        "SystemBookmarkNumber": 1,
        "SellCommodities": {},
        "BuyCommodities": {},
        "UpdateCommodityCount": true,
        "FleetCarrierTransfer": false,
        "Skip": false,
        "Completed": false
    },
    "2": {
        "SystemName": "",
        "StationName": "Construction Site",
        "GalaxyBookmarkType": "Favorites",
        "GalaxyBookmarkNumber": 3,
        "SystemBookmarkType": "Station",
        "SystemBookmarkNumber": 2,
        "SellCommodities": { "ALL": 0 },
        "BuyCommodities": {},
        "UpdateCommodityCount": true,
        "FleetCarrierTransfer": false,
        "Skip": false,
        "Completed": false
    },
    "3": {
        "SystemName": "REPEAT",
        "StationName": "",
        "GalaxyBookmarkType": "",
        "GalaxyBookmarkNumber": 0,
        "SystemBookmarkType": "",
        "SystemBookmarkNumber": 0,
        "SellCommodities": {},
        "BuyCommodities": {},
        "UpdateCommodityCount": false,
        "FleetCarrierTransfer": false,
        "Skip": false,
        "Completed": false
    }
}
```

### Field Reference

#### GlobalShoppingList (optional top-level entry)

| Field | Type | Description |
|---|---|---|
| `BuyCommodities` | object | Items to buy across all waypoints. Format: `{"ItemName": quantity}`. Set quantity to `0` to skip an item. |
| `UpdateCommodityCount` | bool | If `true`, quantities decrement after each purchase |
| `FleetCarrierTransfer` | bool | If `true`, use fleet carrier transfer UI instead of market |
| `Skip` | bool | If `true`, skip the global shopping list entirely |
| `Completed` | bool | Set to `true` by the autopilot when all items are bought |

#### Numbered Waypoints ("1", "2", "3", ...)

| Field | Type | Description |
|---|---|---|
| `SystemName` | string | Target system name. Leave blank `""` when using bookmarks. Set to `"REPEAT"` for a loop waypoint. |
| `StationName` | string | Station/fleet carrier/construction site name. Leave blank `""` to skip docking. |
| `GalaxyBookmarkType` | string | Bookmark tab in galaxy map. See values below. |
| `GalaxyBookmarkNumber` | int | Which bookmark to select (1-based). `0` = disabled. |
| `SystemBookmarkType` | string | Bookmark tab in system map. Usually `"Station"` or `""`. |
| `SystemBookmarkNumber` | int | Which system bookmark to select (1-based). `0` = disabled. |
| `SellCommodities` | object | Items to sell. Use `{"ALL": 0}` to sell everything. Or `{"Gold": 9999}` for specific items. |
| `BuyCommodities` | object | Items to buy at this stop. Format: `{"ItemName": quantity}`. If empty, pulls from GlobalShoppingList. |
| `UpdateCommodityCount` | bool | If `true`, quantities decrement after each purchase |
| `FleetCarrierTransfer` | bool | If `true`, use fleet carrier transfer UI |
| `Comment` | string | Optional note (not used by autopilot) |
| `Skip` | bool | If `true`, autopilot skips this waypoint |
| `Completed` | bool | Set to `true` by autopilot when waypoint is done |

#### GalaxyBookmarkType Values

| Value | Description |
|---|---|
| `"Favorites"` | Your favorited systems |
| `"System"` | System bookmarks |
| `"Body"` | Body bookmarks |
| `"Station"` | Station bookmarks |
| `"Settlement"` | Settlement bookmarks |
| `""` | No galaxy bookmark (uses SystemName for search) |

#### Special Waypoints

- **REPEAT** -- set `"SystemName": "REPEAT"` to loop back to waypoint 1. All waypoints reset their `Completed` flag.
- **Sell everything** -- set `"SellCommodities": {"ALL": 0}` to sell all cargo at that stop.
- **Skip** -- set `"Skip": true` to skip a waypoint without deleting it from the file.

### How Bookmarks Work

The autopilot navigates by opening the galaxy map and clicking on your bookmarks. This means you need to set up bookmarks in-game before creating waypoint files.

1. In Elite Dangerous, open the galaxy map
2. Navigate to your target system
3. Right-click and add to bookmarks (Favorites, System, etc.)
4. Note which tab and position number the bookmark is in
5. Use those values for `GalaxyBookmarkType` and `GalaxyBookmarkNumber` in your JSON

The position number is counted from the top of the bookmark list, starting at 1.

---

## Ship Configuration

Each ship needs its **Roll, Pitch, and Yaw rates** configured for accurate alignment. Go to the **Settings** tab in the GUI and adjust:

- **Roll Rate** (degrees/sec)
- **Pitch Rate** (degrees/sec)
- **Yaw Rate** (degrees/sec)

You can find these values in the ship's outfitting screen under ship stats. Save configurations per ship -- the GUI stores them in `AP.json`.

See [docs/RollPitchYaw.md](docs/RollPitchYaw.md) for details.

---

## Limitations

### Hard Requirements

- **Windows only** -- uses Windows APIs for input simulation
- **1920x1080 only** -- screen regions are calibrated for this resolution. Other resolutions will not work reliably.
- **Borderless Windowed mode** -- fullscreen exclusive breaks screen capture
- **Default orange HUD only** -- the autopilot detects UI elements by their orange color (HSV filtering). Custom HUD colors break detection completely.
- **Docking computer required** -- the autopilot requests docking permission but relies on the game's auto-dock to land

### Not Supported

- Combat or interdiction defense
- Planetary landings
- Mining
- Multicrew
- Custom HUD color schemes
- Multi-monitor setups (captures primary display only)
- Resolutions other than 1920x1080

### Known Quirks

- Construction site approaches can fail if the ship's angle is off
- Fuel scooping may timeout on ships with small scoops
- Planets blocking the nav lock can cause alignment issues
- The autopilot stops after a REPEAT loop resets -- it then continues from waypoint 1

---

## GUI Tabs

| Tab | Purpose |
|---|---|
| **Main** | Start/stop assists, load waypoint files, monitor commodities and flight log |
| **Settings** | Ship RPY rates, timeouts, overlay options |
| **Debug/Test** | Debug output, screen region testing |

---

## Project Structure

```
src/
  autopilot/   - flight logic (alignment, supercruise, jumping, docking)
  ed/          - Elite Dangerous integration (journal, keybinds, station services)
  gui/         - tkinter GUI
  screen/      - screen capture, OCR, color detection, YOLO compass
waypoints/     - waypoint JSON files
configs/       - resolution scaling, screen regions, calibration
docs/          - detailed documentation
templates/     - screen matching templates
locales/       - translations (en, de, fr, ru)
```

---

## Further Documentation

- [Waypoint format details](docs/Waypoint.md)
- [Ship Roll/Pitch/Yaw tuning](docs/RollPitchYaw.md)
- [Autopilot design](docs/Design.md)
- [Waypoint-Anleitung (Deutsch)](docs/HOWTO_Waypoints_DE.md)
