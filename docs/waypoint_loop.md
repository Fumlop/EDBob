# Waypoint Loop

## States
| State | Source | Cleared |
|---|---|---|
| `is_docked` | status.json FlagsDocked | on undock |
| `in_supercruise` | status.json FlagsSupercruise | on SC exit/drop |
| `has_masslock` | status.json FlagsFsdMassLocked | on clear |
| `sc_assist_active` | nav panel activation | on SC drop only |
| `current_waypoint` | waypoint step counter | on mark complete |
| `target_system` | galaxy bookmark | on waypoint change |
| `same_system` | compare cur_system vs target | after jump / on init |

## Init
- [STATUS CHECKS]
- [IS DOCKED?] -> true/false
- [docked = false] select first Waypoint

## Loop Start
## If Docked
- [refuel/repair/rearm]
- [GlobalShopping List - no more to buy here loop end] (we currently just accept two Waypoints)
- [buy/sell]
- [deliever construction complete? -> loop end]
- [select next Waypoint]
- [undock]

### Supercruise (handling)
- [Check SC Status]
  ## [SC=false]
- [Masslock=true -> Boost until cleared]
- [Masslock=false -> init SC]

### Navigation
- [Alignment on target]
- [Same System -> sc_assist]
- [Other System -> FSD] - state needs to be tracked? for finish block?

### Finished FSD
- [Sun avoidance]
- [### Navigation]

### SC Assist (if target System)
- [NavPanelselect - remember last state - clears on drop only]
- [Activate Assist if off - wait for settle]
- [Monitor state and occlusion - wait for drop]
	## occlusion/body/sc_assist missing
	- [occlusion/body evation]
	## interdiction
	- [interdiction submit code -> back to SC]

### Arrival
- [Docking procedure]
	Denied check masslock.... realign without sc and 25% throttle for 4s? (3times max)
- [Wait for status DOCKED]
- [Loop back if docked]

