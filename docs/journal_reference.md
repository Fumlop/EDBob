# Elite Dangerous Journal Reference

The game writes JSON events to rotating log files in the journal directory.
Before adding screen scraping for a new feature, check if there's a journal
event that gives the same info -- journal data is 100% reliable, screen
scraping is not.

Full documentation: https://elite-journal.readthedocs.io/en/latest/

## Journal File Location

```
%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous\Journal.*.log
```

Files are named `Journal.YYMMDDHHMMSS.01.log` and rotate when they hit 500k lines.

## Events We Already Parse (EDJournal.py)

| Event | What we use it for |
|-------|-------------------|
| `FSDJump` | Detect system arrival, read star class, location |
| `FSDTarget` | Read jump target system name + remaining jumps |
| `SupercruiseEntry` | Set status to `in_supercruise` |
| `SupercruiseExit` | Set status to `in_space` |
| `SupercruiseDestinationDrop` | Read drop type (station, construction, etc) |
| `Docked` | Set status to `docked`, read station type/name |
| `Undocked` | Set status to `in_station` (undocking sequence) |
| `DockingRequested` | Track docking request state |
| `DockingCancelled` | Clear docking request state |
| `Location` | Initial position on game load |
| `Music` | Track music_track (DockingComputer, NoTrack, MainMenu, etc) |
| `NavRoute` | Route file written (triggers NavRouteParser) |
| `NavRouteClear` | Route cleared |
| `StartJump` | FSD countdown started |

## Useful Events We DON'T Parse Yet

These could replace screen scraping or enable new features:

### Travel

| Event | Potential use |
|-------|--------------|
| `ApproachBody` | Detect entering orbital cruise -- could trigger planet approach logic |
| `LeaveBody` | Detect leaving orbital cruise -- confirm planet departure |
| `DockingGranted` | Know which pad was assigned (LandingPad field) |
| `DockingDenied` | Know why docking failed (Reason field) |
| `DockingTimeout` | Detect expired docking request |
| `StartJump` | Has `JumpType` field: "Hyperspace" vs "Supercruise" to distinguish jump types |

### State Detection

| Event | Potential use |
|-------|--------------|
| `FuelScoop` | Detect fuel scooping start/end, know exact fuel level |
| `Scanned` | Ship was scanned by NPC -- could trigger evasive action |
| `BeingInterdicted` | Know who is interdicting (already use status.json flag, but journal has attacker name) |
| `Interdicted` | Result of interdiction (submitted/escaped) |
| `EscapeInterdiction` | Confirm successful escape |
| `RebootRepair` | Know when reboot/repair is happening |
| `SystemsShutdown` | Thargoid shutdown -- need to wait for reboot |
| `USSDrop` | Dropped at USS -- know the signal type |

### Ship Info

| Event | Potential use |
|-------|--------------|
| `ModuleInfo` | Modules changed -- could read module loadout |
| `Synthesis` | Player synthesized something (FSD boost, ammo, etc) |
| `JetConeBoost` | Neutron star boost detected |
| `JetConeDamage` | Module damaged by jet cone |
| `ReservoirReplenished` | Fuel tank management |
| `AfmuRepairs` | AFMU repairing a module |

### Social / Misc

| Event | Potential use |
|-------|--------------|
| `ReceiveText` | NPC or player messages (could detect "scan detected" warnings) |
| `Friends` | Friend status changes |
| `Music` | Already parsed -- mood tracks indicate game state reliably |

## Music Tracks (already parsed)

The `Music` event `MusicTrack` field values:

| Track | Game state |
|-------|-----------|
| `NoTrack` | Silence -- outside station after autodock, or in normal flight |
| `DockingComputer` | Autodock/autolaunch active |
| `MainMenu` | At main menu (game not running) |
| `Supercruise` | In supercruise |
| `SystemMap` | System map open |
| `GalaxyMap` | Galaxy map open |
| `Exploration` | FSS/DSS active |
| `Combat_Dogfight` | In combat |
| `Combat_Unknown` | Hostile detected |
| `Starport` | Inside a starport |
| `Unknown_Encounter` | Approaching unknown signal |

## status.json vs Journal

| Need | Use |
|------|-----|
| Real-time flag checks (in SC? docked? mass locked?) | `status.json` -- updates every ~1s |
| One-time event detection (jumped, docked, undocked) | Journal -- written once when event happens |
| Continuous state (fuel level, cargo, pips) | `status.json` |
| Historical data (where did we jump from, star class) | Journal |

See also: [docs/status_json.md](status_json.md) for status.json flag reference.
