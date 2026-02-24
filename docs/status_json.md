# Elite Dangerous status.json Reference

Elite Dangerous writes `status.json` to the journal directory every few seconds.
EDBob reads it via `StatusParser` to get real-time ship state without screen scraping.

Source: [elite-journal.readthedocs.io/en/latest/Status%20File.html](https://elite-journal.readthedocs.io/en/latest/Status%20File.html)

## File Location

```
%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\status.json
```

## File Structure

```json
{
  "timestamp": "2026-02-24T06:27:57Z",
  "event": "Status",
  "Flags": 16842765,
  "Flags2": 0,
  "Pips": [4, 4, 4],
  "FireGroup": 0,
  "GuiFocus": 0,
  "Fuel": { "FuelMain": 32.0, "FuelReservoir": 0.63 },
  "Cargo": 0
}
```

## GuiFocus Values

| Value | Meaning |
|-------|---------|
| 0 | NoFocus (flying) |
| 1 | InternalPanel (right panel) |
| 2 | ExternalPanel (left panel) |
| 3 | CommsPanel (top panel) |
| 4 | RolePanel (bottom panel) |
| 5 | StationServices |
| 6 | GalaxyMap |
| 7 | SystemMap |
| 8 | Orrery |
| 9 | FSS mode |
| 10 | SAA mode |
| 11 | Codex |

## Flags (32-bit bitmask)

| Bit | Value | Constant in EDAP_data.py | Meaning |
|-----|-------|--------------------------|---------|
| 0 | 1 | `FlagsDocked` | On a landing pad (station or planet) |
| 1 | 2 | `FlagsLanded` | On planet surface (not a landing pad) |
| 2 | 4 | `FlagsLandingGearDown` | Landing gear deployed |
| 3 | 8 | `FlagsShieldsUp` | Shields active |
| 4 | 16 | `FlagsSupercruise` | In supercruise |
| 5 | 32 | `FlagsFlightAssistOff` | Flight assist off |
| 6 | 64 | `FlagsHardpointsDeployed` | Hardpoints deployed |
| 7 | 128 | `FlagsInWing` | In a wing |
| 8 | 256 | `FlagsLightsOn` | Ship lights on |
| 9 | 512 | `FlagsCargoScoopDeployed` | Cargo scoop deployed |
| 10 | 1024 | `FlagsSilentRunning` | Silent running active |
| 11 | 2048 | `FlagsScoopingFuel` | Fuel scooping |
| 12 | 4096 | `FlagsSrvHandbrake` | SRV handbrake on |
| 13 | 8192 | `FlagsSrvTurret` | SRV turret view |
| 14 | 16384 | `FlagsSrvUnderShip` | SRV turret retracted |
| 15 | 32768 | `FlagsSrvDriveAssist` | SRV drive assist on |
| 16 | 65536 | `FlagsFsdMassLocked` | FSD mass locked |
| 17 | 131072 | `FlagsFsdCharging` | FSD charging (SC or hyperspace) |
| 18 | 262144 | `FlagsFsdCooldown` | FSD cooldown after jump |
| 19 | 524288 | `FlagsLowFuel` | Fuel below 25% |
| 20 | 1048576 | `FlagsOverHeating` | Heat above 100% |
| 21 | 2097152 | `FlagsHasLatLong` | Altimeter visible (near body) |
| 22 | 4194304 | `FlagsIsInDanger` | In danger zone |
| 23 | 8388608 | `FlagsBeingInterdicted` | Being interdicted |
| 24 | 16777216 | `FlagsInMainShip` | In main ship |
| 25 | 33554432 | `FlagsInFighter` | In ship-launched fighter |
| 26 | 67108864 | `FlagsInSRV` | In SRV |
| 27 | 134217728 | `FlagsAnalysisMode` | HUD in analysis mode |
| 28 | 268435456 | `FlagsNightVision` | Night vision active |
| 29 | 536870912 | `FlagsAverageAltitude` | Altitude from avg radius (OC/DRP mode) |
| 30 | 1073741824 | `FlagsFsdJump` | In hyperspace/SC jump |
| 31 | 2147483648 | `FlagsSrvHighBeam` | SRV high beam on |

## Flags2 (additional bitmask, Odyssey+)

| Bit | Value | Constant in EDAP_data.py | Meaning |
|-----|-------|--------------------------|---------|
| 0 | 1 | `Flags2OnFoot` | On foot |
| 1 | 2 | `Flags2InTaxi` | In taxi/dropship/shuttle |
| 2 | 4 | `Flags2InMulticrew` | In someone else's ship |
| 3 | 8 | `Flags2OnFootInStation` | On foot in station |
| 4 | 16 | `Flags2OnFootOnPlanet` | On foot on planet |
| 5 | 32 | `Flags2AimDownSight` | Aiming down sight |
| 6 | 64 | `Flags2LowOxygen` | Low oxygen |
| 7 | 128 | `Flags2LowHealth` | Low health |
| 8 | 256 | `Flags2Cold` | Cold |
| 9 | 512 | `Flags2Hot` | Hot |
| 10 | 1024 | `Flags2VeryCold` | Very cold |
| 11 | 2048 | `Flags2VeryHot` | Very hot |
| 12 | 4096 | `Flags2GlideMode` | Glide mode (orbital drop) |
| 13 | 8192 | `Flags2OnFootInHangar` | On foot in hangar |
| 14 | 16384 | `Flags2OnFootSocialSpace` | On foot in social space |
| 15 | 32768 | `Flags2OnFootExterior` | On foot exterior |
| 16 | 65536 | `Flags2BreathableAtmosphere` | Breathable atmosphere |
| 17 | 131072 | `Flags2TelepresenceMulticrew` | Telepresence multicrew |
| 18 | 262144 | `Flags2PhysicalMulticrew` | Physical multicrew |
| 19 | 524288 | `Flags2FsdHyperdriveCharging` | Hyperdrive charging (system jump only) |
| 20 | 1048576 | `Flags2FsdScoActive` | SCO (supercruise overcharge) active |

## Notes

- `FlagsFsdCharging` (bit 17) is set for BOTH supercruise and hyperspace jumps
- `Flags2FsdHyperdriveCharging` (bit 19) is set ONLY for hyperspace jumps -- use this to distinguish SC from hyperspace
- `FlagsFsdJump` (bit 30) is set while the ship is in the jump animation
- `FlagsHasLatLong` + `FlagsAverageAltitude` together indicate orbital cruise (OC) near a body
- `FlagsHasLatLong` without `FlagsAverageAltitude` indicates surface proximity (2km/SURF altimeter)
- `Flags2FsdScoActive` (bit 20) is not in the official journal docs -- added in a later game update for SCO boost detection
