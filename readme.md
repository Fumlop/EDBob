# EDAPGui - Elite Dangerous Autopilot

Waypoint Assist autopilot for Elite Dangerous. Flies trade routes automatically using galaxy map bookmarks and commodity lists.

## Requirements

- Windows 10/11
- Python 3.11+
- Elite Dangerous in **Borderless Windowed** mode at **1920x1080**

Keybindings are auto-detected from your Elite Dangerous configuration -- no manual setup needed.

## Install & Run

Double-click `start_ed_ap.bat`. On first run it creates a virtual environment and installs all dependencies automatically.

Alternatively, run `install_requirements.bat` first for a separate install step.

## Usage

1. Set bookmarks in the Elite Dangerous galaxy map
2. Create a waypoint JSON file in `waypoints/` (see below)
3. Start EDAP, open the **Waypoints** tab, click **Open** and load your file
4. Switch to the **Main** tab and enable **Waypoint Assist**
5. The autopilot flies each waypoint, buys/sells commodities, and loops if configured

To stop: uncheck **Waypoint Assist**. The autopilot finishes the current action and stops.

## Waypoint Files

Waypoint files are JSON files in `waypoints/`. They define a route with a global shopping list and numbered waypoints.

Minimal example:

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

Key fields:
- **GalaxyBookmarkType/Number** -- galaxy map bookmark to select (e.g. Favorites #2)
- **SystemBookmarkType/Number** -- system map bookmark to select
- **SellCommodities** -- `{"ALL": 0}` sells everything
- **BuyCommodities** -- items to buy at this stop (or pulled from GlobalShoppingList)
- **REPEAT waypoint** -- `"SystemName": "REPEAT"` resets all waypoints and loops

Detailed guide (German): [docs/HOWTO_Waypoints_DE.md](docs/HOWTO_Waypoints_DE.md)

## Project Structure

```
src/
  autopilot/   - autopilot logic (alignment, supercruise, docking)
  ed/          - Elite Dangerous journal parsing, keybinds, station services
  gui/         - tkinter GUI
  screen/      - screen capture and region detection
waypoints/     - waypoint JSON files
docs/          - documentation
```
