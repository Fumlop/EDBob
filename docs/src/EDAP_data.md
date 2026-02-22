# EDAP_data.py -- Static Game Data

## Purpose

Static data constants for Elite Dangerous: status flags, GUI focus IDs, ship names/sizes, supercruise handling rates, and commodity lists. Referenced throughout the codebase.
Lives in `src/core/EDAP_data.py`.

## Status.json Flags1 Constants

| Constant | Value | Description |
|---|---|---|
| `FlagsDocked` | 1 << 0 | On a landing pad |
| `FlagsLanded` | 1 << 1 | On planet surface |
| `FlagsLandingGearDown` | 1 << 2 | Landing gear deployed |
| `FlagsShieldsUp` | 1 << 3 | Shields active |
| `FlagsSupercruise` | 1 << 4 | In supercruise |
| `FlagsFlightAssistOff` | 1 << 5 | Flight assist disabled |
| `FlagsHardpointsDeployed` | 1 << 6 | Hardpoints out |
| `FlagsInWing` | 1 << 7 | In a wing |
| `FlagsLightsOn` | 1 << 8 | Ship lights on |
| `FlagsCargoScoopDeployed` | 1 << 9 | Cargo scoop open |
| `FlagsSilentRunning` | 1 << 10 | Silent running |
| `FlagsScoopingFuel` | 1 << 11 | Fuel scooping |
| `FlagsFsdMassLocked` | 1 << 16 | FSD mass locked |
| `FlagsFsdCharging` | 1 << 17 | FSD charging (SC or jump) |
| `FlagsFsdCooldown` | 1 << 18 | FSD on cooldown |
| `FlagsLowFuel` | 1 << 19 | Fuel < 25% |
| `FlagsOverHeating` | 1 << 20 | Heat > 100% |
| `FlagsHasLatLong` | 1 << 21 | Altimeter visible |
| `FlagsIsInDanger` | 1 << 22 | In danger zone |
| `FlagsBeingInterdicted` | 1 << 23 | Being interdicted |
| `FlagsInMainShip` | 1 << 24 | In main ship |
| `FlagsInFighter` | 1 << 25 | In fighter |
| `FlagsInSRV` | 1 << 26 | In SRV |
| `FlagsAnalysisMode` | 1 << 27 | HUD analysis mode |
| `FlagsNightVision` | 1 << 28 | Night vision |
| `FlagsAverageAltitude` | 1 << 29 | Altitude from average radius |
| `FlagsFsdJump` | 1 << 30 | Jumping (SC or system) |
| `FlagsSrvHighBeam` | 1 << 31 | SRV high beam |

## Status.json Flags2 Constants

| Constant | Value | Description |
|---|---|---|
| `Flags2OnFoot` | 1 << 0 | On foot |
| `Flags2InTaxi` | 1 << 1 | In taxi/dropship |
| `Flags2InMulticrew` | 1 << 2 | In someone else's ship |
| `Flags2OnFootInStation` | 1 << 3 | On foot in station |
| `Flags2OnFootOnPlanet` | 1 << 4 | On foot on planet |
| `Flags2AimDownSight` | 1 << 5 | Aiming down sight |
| `Flags2GlideMode` | 1 << 12 | Glide mode |
| `Flags2FsdHyperdriveCharging` | 1 << 19 | Hyperdrive charging (system jump) |
| `Flags2FsdScoActive` | 1 << 20 | SCO active |

## GuiFocus Constants

| Constant | Value | Description |
|---|---|---|
| `GuiFocusNoFocus` | 0 | Ship cockpit view |
| `GuiFocusInternalPanel` | 1 | Right hand panel |
| `GuiFocusExternalPanel` | 2 | Left hand (nav) panel |
| `GuiFocusCommsPanel` | 3 | Top panel |
| `GuiFocusRolePanel` | 4 | Bottom panel |
| `GuiFocusStationServices` | 5 | Station services |
| `GuiFocusGalaxyMap` | 6 | Galaxy map |
| `GuiFocusSystemMap` | 7 | System map |
| `GuiFocusOrrery` | 8 | Orrery view |
| `GuiFocusFSS` | 9 | Full Spectrum Scanner |
| `GuiFocusSAA` | 10 | Surface Analysis Scanner |
| `GuiFocusCodex` | 11 | Codex |

## Ship Data Dictionaries

### `ship_name_map`

Maps journal ship ID (lowercase) to display name. 47 ships including Cobra Mk V, Corsair, Mandalay, Panther Clipper, Caspian Explorer, Type-11 Prospector.

### `ship_size_map`

Maps journal ship ID to landing pad size: `"S"` (small), `"M"` (medium), `"L"` (large), `""` (fighters/SRV).

### `ship_rpy_sc_50`

Ship roll/pitch/yaw rates in deg/sec at 50% supercruise throttle. Keys: `RollRate`, `PitchRate`, `YawRate`, `SunPitchUp+Time`. Data from forum post by 'marx'. 44 ships.

### `ship_rpy_sc_100`

Ship roll/pitch/yaw rates in deg/sec at 100% supercruise throttle. Same format as `ship_rpy_sc_50`. 44 ships.

## Commodity Data

### `commodities`

Dict mapping category name to list of commodity names. 15 categories:
- Chemicals (13 items including Tritium)
- Consumer Items (5)
- Foods (9)
- Industrial Materials (9)
- Legal Drugs (7)
- Machinery (23)
- Medicines (6)
- Metals (24 including Platinum Alloy, Hafnium 178)
- Minerals (28)
- Salvage (72)
- Slavery (2)
- Technology (18)
- Textiles (5)
- Waste (4)
- Weapons (5)

### Module-Level Functions

| Function | Returns | Description |
|---|---|---|
| `sorted_commodities()` | list[str] | Returns a flat, alphabetically sorted list of all commodity names across all categories. |

## Notes

- Ship data sourced from Frontier forums and EDMarketConnector
- `SunPitchUp+Time` is a per-ship adjustment for sun avoidance pitch timing (negative = less time needed, positive = more)
- Some ship IDs use historical names (e.g. `independant_trader` for Keelback, `clipper` for Panther Clipper)
- Flags2 bits 21-31 are reserved for future use
