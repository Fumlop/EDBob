# Anleitung: Waypoint-Datei und Autopilot

## Voraussetzungen

- Elite Dangerous im **Fenstermodus (Borderless)** mit **1920x1080** Aufloesung
- EDAP gestartet, Elite Dangerous sichtbar auf dem Bildschirm
- Lesezeichen (Bookmarks) in der Galaxiekarte gesetzt

---

## Waypoint-Datei erstellen

Die Waypoint-Datei ist eine `.json`-Datei im Ordner `waypoints/`. Beispiel: `waypoints/haul_favs.json`.

### Aufbau

```json
{
    "GlobalShoppingList": {
        "BuyCommodities": {
            "Aluminium": 40053,
            "Steel": 47109,
            "Titanium": 28974
        },
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

### Felder erklaert

#### GlobalShoppingList (Pflicht)

Muss immer vorhanden sein. Enthaelt die globale Einkaufsliste.

| Feld | Beschreibung |
|------|-------------|
| `BuyCommodities` | Waren und Mengen die insgesamt gekauft werden sollen. Zaehlt automatisch runter wenn `UpdateCommodityCount: true`. |
| `UpdateCommodityCount` | `true` = Mengen werden nach jedem Kauf/Verkauf aktualisiert |
| `Skip` | `true` = Einkaufsliste wird ignoriert |

#### Waypoints (1, 2, 3, ...)

Jeder Waypoint ist ein Ziel das der Autopilot anfliegt.

| Feld | Beschreibung |
|------|-------------|
| `SystemName` | Systemname (leer lassen wenn Lesezeichen benutzt wird) |
| `StationName` | Stationsname (z.B. "Construction Site" fuer Baustellen) |
| `GalaxyBookmarkType` | Lesezeichen-Typ in der Galaxiekarte: `"Favorites"`, `"Station"`, etc. |
| `GalaxyBookmarkNumber` | Nummer des Lesezeichens (1 = erstes, 2 = zweites, ...) |
| `SystemBookmarkType` | Lesezeichen-Typ in der Systemkarte: `"Station"`, etc. |
| `SystemBookmarkNumber` | Nummer des Lesezeichens in der Systemkarte |
| `SellCommodities` | Waren verkaufen. `{"ALL": 0}` = alles verkaufen |
| `BuyCommodities` | Waren kaufen (leer = nichts kaufen, oder aus GlobalShoppingList) |
| `UpdateCommodityCount` | `true` = GlobalShoppingList Mengen aktualisieren |
| `FleetCarrierTransfer` | `true` = Fleet Carrier Transfer statt normaler Kauf/Verkauf |
| `Skip` | `true` = Waypoint ueberspringen |
| `Completed` | Wird automatisch auf `true` gesetzt wenn erledigt |

#### REPEAT Waypoint

Ein Waypoint mit `"SystemName": "REPEAT"` setzt alle Waypoints auf `Completed: false` zurueck und startet die Schleife von vorne. Nützlich fuer wiederholte Handelsrouten.

---

## Lesezeichen in Elite Dangerous

Die Lesezeichen-Nummern in der JSON entsprechen der Reihenfolge in der Galaxiekarte/Systemkarte.

1. Galaxiekarte oeffnen
2. Lesezeichen setzen (Favoriten, Stationen, etc.)
3. Die Nummer zaehlt von oben: erstes Lesezeichen = 1, zweites = 2, etc.

**Beispiel:**
- `"GalaxyBookmarkType": "Favorites"` + `"GalaxyBookmarkNumber": 2` = das zweite Lesezeichen unter Favoriten
- `"SystemBookmarkType": "Station"` + `"SystemBookmarkNumber": 1` = die erste Station in der Systemkarte

---

## Datei laden und Autopilot starten

1. **EDAP starten** (Elite Dangerous muss laufen und sichtbar sein)
2. **Tab "Waypoints"** im EDAP-Fenster oeffnen
3. **"Open"** klicken und die `.json`-Datei aus `waypoints/` auswaehlen
4. Waypoints werden in der Liste angezeigt
5. Auf dem **Tab "Main"** die Checkbox **"Waypoint Assist"** aktivieren
6. Der Autopilot startet und arbeitet die Waypoints der Reihe nach ab

### Stoppen

- Checkbox **"Waypoint Assist"** deaktivieren
- Der Autopilot stoppt nach der aktuellen Aktion

### Zuruecksetzen

- Im Tab "Waypoints" den Button **"Reset"** klicken
- Setzt alle `Completed`-Flags zurueck auf `false`

---

## Typischer Ablauf: Handelsroute mit Baustelle

1. Lesezeichen setzen:
   - Favorit 2 = System mit Handelsstation
   - Favorit 3 = System mit Baustelle
2. Waypoint-Datei erstellen:
   - GlobalShoppingList mit benoetigten Waren und Mengen
   - Waypoint 1: Handelsstation (kaufen)
   - Waypoint 2: Baustelle (alles verkaufen mit `"ALL": 0`)
   - Waypoint 3: REPEAT
3. Datei laden, Waypoint Assist aktivieren
4. Autopilot fliegt zur Station, kauft ein, fliegt zur Baustelle, verkauft, wiederholt

---

## Wichtig

- **Nur 1920x1080 Fenstermodus** wird unterstuetzt
- Elite Dangerous darf **nicht minimiert** sein
- Lesezeichen muessen **vor dem Start** gesetzt sein
- Die GlobalShoppingList ist **Pflicht** in jeder Waypoint-Datei
- `UpdateCommodityCount: true` zaehlt die Mengen automatisch runter
