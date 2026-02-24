# src/core/EDAP_data.py (245 lines)

Static constants for Elite Dangerous game state. No classes, no I/O.

## Status Flags

Bitmask constants for `status.json` Flags field:

```
FlagsDocked, FlagsLanded, FlagsLandingGearDown, FlagsShieldsUp,
FlagsSupercruise, FlagsFlightAssistOff, FlagsHardpointsDeployed,
FlagsFsdMassLocked, FlagsFsdCharging, FlagsFsdCooldown, FlagsFsdJump,
FlagsLowFuel, FlagsOverHeating, FlagsBeingInterdicted,
FlagsInMainShip, FlagsInFighter, FlagsInSRV, FlagsAnalysisMode,
FlagsHasLatLong, FlagsAverageAltitude, ...
```

Flags2 (Odyssey+): `Flags2OnFoot`, `Flags2InTaxi`, `Flags2GlideMode`,
`Flags2FsdHyperdriveCharging`, `Flags2FsdScoActive`, ...

## GuiFocus Constants

`GuiFocusNoFocus` (0), `GuiFocusExternalPanel` (2), `GuiFocusStationServices` (5),
`GuiFocusGalaxyMap` (6), `GuiFocusSystemMap` (7), ...

## Ship Data Maps

| Map | Key | Value |
|-----|-----|-------|
| `ship_size_map` | Journal name (e.g. `'anaconda'`) | Size (`'S'`/`'M'`/`'L'`) |
| `ship_name_map` | Journal name | Display name (e.g. `'Anaconda'`) |
| `ship_rpy_sc_50` | Journal name | `[pitch, roll, yaw]` rates at SC 50% |

## No Dependencies

Pure data file. No imports from project modules.
