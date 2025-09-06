# Waypoint Editor
Waypoints are Systems that are captured in a waypoints.json file and read and processed by this Autopilot.  An example waypoint file is below:

## Waypoint Editor
The simplest way to configure a waypoint file is to use the Waypoint Editor tool (with installer) written in C#, available here: [EDAP-Waypoint-Editor](https://github.com/Stumpii/EDAP-Waypoint-Editor). At some point, the features will be added to ED_AP.

![Alt text](../screen/WaypointEditorWaypoints.png?raw=true "Waypoint Editor - Waypoints")

### Main buttons

* New
* Open
* Save
* Save As
* Import Spansh CSV
* Import from Inara

### Waypoints List

![Alt text](../screen/WaypointEditorWaypoints1.png?raw=true "Waypoint Editor - Waypoints")

The list...

### Waypoints Options

![Alt text](../screen/WaypointEditorWaypoints2.png?raw=true "Waypoint Editor - Waypoints")

* Gal
  * Typ
  * Num
* Sys
  * typ
  * Num
* Upda
* Flle

### Buy/Sell Commodities

![Alt text](../screen/WaypointEditorWaypoints3.png?raw=true "Waypoint Editor - Waypoints")

* Name
* Qua
* Add/Sub
* Up/Down
* Add/Del

## Global Shopping List
A set of waypoints can be endlessly repeated by using a special row at the end of the waypoint file with the system name as **'REPEAT'**. When hitting this record and as long as **Skip** is not ture, the Waypoint Assist will start from the top jumping through the defined Systems until the user ends the Waypoint Assist.

![Alt text](../screen/WaypointEditorShoppingList.png?raw=true "Waypoint Editor - Global Shopping List")

### Options

![Alt text](../screen/WaypointEditorShoppingList1png?raw=true "Waypoint Editor - Global Shopping List")

* Upda

### Global Buy Commodities

![Alt text](../screen/WaypointEditorShoppingList2.png?raw=true "Waypoint Editor - Global Shopping List")

* Name
* Qua
* Add/Sub
* Up/Down
* Add/Del
