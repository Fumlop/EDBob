# Planetary Settlement Approach -- Implementation Plan

Updated with lessons from test_oc_nav.py (session 2026-02-26).

## Problem Statement

SC Assist does NOT land on planets. It only orbits. The current EDAP code
actually *evades* when `ApproachBody` fires. For planetary settlements and
construction depots on moons/planets, we need a fully autonomous descent
sequence.

---

## Strategy: "Let SC Assist Orbit, Then Dive" (confirmed v1 approach)

```
Deep SC --> SC Assist orbits body --> Confirm orbit stable
        --> Wait for dive window (glideslope_angle + heading) --> Dive 45 deg
        --> Glide (passive) --> Post-glide compass approach --> Dock
```

The "offset approach" and "manual pre-orbital align" strategies were considered
and rejected. SC Assist reliably puts us in belly-down orbit. We use that.

---

## Phase Breakdown

### Phase 0: Deep SC Approach (EXISTING)

Compass align + SC Assist toward target. No changes needed.

**Note**: The compass points at the settlement which is on the planet surface.
Following it straight in is fine -- SC Assist handles the orbital entry.
We do NOT need to worry about approach angle during deep SC.

---

### Phase 1: OC Detection + Orbit Confirmation

**Detection**: `FlagsSupercruise AND FlagsHasLatLong AND FlagsAverageAltitude`

OC flags can fire early (~990km altitude). The `ApproachBody` journal event
is a more reliable "we are really in OC" signal. Either way, we start reading
`Lat/Lon/Alt/Heading` from `status.json` as soon as OC flags are set.

**Orbit confirmation** (must come before anything else):
- SC Assist puts us in a belly-down orbit (canopy toward planet, top-down)
- We MUST wait for a stable orbit before taking any control inputs
- Detection: altitude drift < 10% for 10 continuous seconds
- If alt drifts > 10%: reset timer

**Why this matters**: If we act before orbit is stable, the ship orientation
is undefined and yaw/pitch inputs produce unpredictable results.

---

### Phase 2: Wait for Dive Window

**Available data from status.json:**
- `Latitude`, `Longitude` (float, degrees)
- `Heading` (int, degrees, 0=N)
- `Altitude` (float, meters)
- `PlanetRadius` (float, meters)

**Target position from waypoint:**
- `Latitude`, `Longitude` (IsPlanetary waypoint fields)

**Computed:**
```python
bearing  = bearing_to(lat, lon, tgt_lat, tgt_lon)
hdg_err  = heading_diff(heading, bearing)         # signed, +R/-L
d_surf   = haversine_distance(lat, lon, tgt_lat, tgt_lon, planet_r)  # surface arc
d3       = dist_3d(lat, lon, alt, tgt_lat, tgt_lon, planet_r)        # straight-line
angle    = glideslope_angle(alt, d3)                # atan2(alt, d3), degrees
```

**IMPORTANT -- glideslope_angle is NOT the ship's pitch angle.**
It is the geometric elevation angle at the target looking up to the ship.
- 0 deg = ship is on the horizon (very far away)
- 90 deg = ship is directly overhead
- 35-38 deg = good dive window (confirmed from test runs)

The angle tells you WHEN you are in position to dive.
It does NOT tell you how much to pitch.

**Dive window conditions** (all must be true):
```
35.0 <= glideslope_angle <= 38.0
dist_3d / alt <= 2.0
|heading_diff| < 3.0 deg
```

**Heading alignment strategy** (open question):
- Active yaw in OC (post SC Assist off) was unreliable in tests
- Orbit naturally carries the ship -- target comes into bearing over time
- For v1: wait passively for orbit to bring heading into alignment window
  rather than actively yawing

---

### Phase 4: Dive

**Initiation**:
1. Lock `lock_angle = glideslope_angle` at trigger (freeze reference)
2. Throttle to zero
3. Pitch +45 deg toward planet
4. Poll altitude: when alt drops to 60% of entry alt, pitch -45 deg (pullback)
5. Transition to dive correction loop

**Dive correction** (each status cycle):
```python
current_angle = glideslope_angle(alt, dist_3d(...))
error = current_angle - lock_angle    # + = too shallow, - = too steep

band = [lock_angle - 0.4, lock_angle + 0.4]
if current_angle < band.lo:  pitch toward planet (steepen)
if current_angle > band.hi:  pitch away (flatten)
if |hdg_err| > 2:            yaw to bearing
```

**Stop condition**: `Flags2GlideMode` set.

**Known problem from test runs -- dive correction does NOT work yet:**

Observed behavior:
- Ship pitched ~80 deg nose-toward-planet visually
- glideslope stayed at ~40 deg, never reached lock_angle=35 deg
- Only after overpitching enough nose-AWAY from target did glideslope rise

Root cause: **unclear, but glideslope feedback via pitch pulses does not work.**

ED does not simulate real orbital mechanics -- gravity does not continuously
pull the ship at 30 km/s. The ship moves in the direction it is pointed (with
lag). Throttle zero still means ~30 km/s, but that velocity follows the nose,
not an independent orbital arc.

Likely causes (need PlanetaryTracker data to confirm):
- Pitch pulses too short: game needs sustained hold before altitude changes
- status.json altitude ticks (1s) too coarse to track fast OC position changes
- Heading was off-target during dive: ship was flying past/away from settlement
  at 30 km/s, so dist_3d grew even as alt dropped -> glideslope stayed high
- Combination: heading not aligned + insufficient sustained pitch

The overpitch-away "fix" that finally moved glideslope may have worked by
accidentally re-aligning the heading toward the target, shrinking dist_3d.

**What is confirmed**: reactive pitch correction loop produced wrong results.
**What is unknown**: whether the cause is heading drift, pitch lag, or both.

**Critical constraint: throttle zero in OC = still ~30 km/s.**
Orbital velocity cannot be bled in any useful timeframe. "Wait for velocity
to align with nose" is not viable -- the ship is always at orbital speed in OC.

**Consequence: glideslope correction via pitch is unworkable in OC entirely.**
There is no throttle state that removes orbital velocity before glide engages.

**v1 dive strategy: commit and hold, no correction loop.**
1. Align heading to target bearing BEFORE committing to dive
2. At trigger (glideslope 35-38 deg): pitch toward planet at a fixed angle
   and hold it -- do NOT try to reactively correct glideslope mid-dive
3. Let SC physics and gravity do the work; glide will engage when conditions
   are met regardless of what the nose is doing
4. The heading alignment (step 1) is the only meaningful pre-dive correction
   we can make; everything after trigger is committed

The glideslope_angle is still useful as a TRIGGER (when to start the dive),
not as a feedback variable for a control loop.

---

### Phase 5: Glide (passive)

**Detection**: `Flags2GlideMode`

- Hold current attitude -- do not fight the glide
- Speed is fixed at 2500 m/s
- Aggressive yaw causes pilot blackout -- avoid
- Alt drops from ~20km to ~4km in ~10-15s
- Exits ~3-5km from settlement (from test data)
- After glide: `NOT FlagsSupercruise AND FlagsHasLatLong AND NOT Flags2GlideMode`

Glide rules (for future active management):
- Entry angle: -5 to -60 deg (optimal: -40 to -50 deg)
- Too steep = emergency drop (hull damage)
- Too shallow = early exit (far from target)

v1: passive wait. If dive angle was ~35-38 deg at trigger, glide deposits
us close enough for compass approach.

---

### Phase 6: Post-Glide Approach

**Detection**: NOT `FlagsSupercruise`, `FlagsHasLatLong`, NOT `Flags2GlideMode`

- Compass points at settlement -- use existing alignment code
- Maintain minimum altitude (don't crash into terrain)
- `ApproachSettlement` journal event fires when close
- Request docking when in range
- Existing docking code handles final landing

---

## Data Sources Summary

| Data | Source | Reliability |
|------|--------|-------------|
| In OC? | status.json: Supercruise+HasLatLong+AverageAltitude | High |
| In glide? | status.json: Flags2GlideMode | High |
| Orbit stable? | status.json: Altitude drift < 10% for 10s | High |
| Current position | status.json: Lat/Lon/Alt/Heading | High |
| Settlement position | Waypoint: IsPlanetary Latitude/Longitude | High |
| glideslope_angle | Computed: atan2(alt, dist_3d) | High |
| Compass direction | Screen: existing navball detection | Medium (backup) |

---

## Implementation Order

### Step 1 (DONE): EDNavUtils
- `detect_phase()`, `is_orbiting()`, `is_above_planet()`
- `haversine_distance()`, `bearing_to()`, `dist_3d()`, `heading_diff()`
- `glideslope_angle()` with NOT-ship-pitch note

### Step 2 (DONE): Waypoint format
- `IsPlanetary: true`, `Latitude`, `Longitude`
- `PlanetRadius` comes from `status.json` live -- not stored in waypoint
- See `waypoints/example_planetary.json` (Voelundr Hub as test reference)

### Step 3 (NEXT): PlanetaryTracker (debug logging)
- Background thread, polls StatusParser, logs CSV until docked
- Target lat/lon from waypoint fields
- Columns: timestamp, phase, lat, lon, alt, heading, planet_r,
           bearing, dist_surface, dist_3d, glideslope_angle, hdg_err
- Needed to validate dive window timing before implementing autopilot

### Step 4: Journal integration
- `ApproachBody` event: confirm OC entry
- `ApproachSettlement` event: could also provide lat/lon as fallback

### Step 5: ED_AP.py -- planetary branch in sc_assist / waypoint_assist
- Detect IsPlanetary waypoint
- Don't evade on ApproachBody -- branch to planetary descent sequence
- State machine: WAIT_OC -> ORBIT_CHECK -> DEACTIVATE_SCA -> DIVE_WINDOW -> DIVE -> GLIDE -> POSTGLIDE

### Step 6: Post-glide compass approach + docking
- Re-use existing compass alignment
- Terrain altitude management

---

## Open Questions

1. **Heading alignment in OC** -- active yaw unreliable. Wait for orbit to
   bring target into view naturally? Needs data from PlanetaryTracker runs.

2. **Polar settlements** -- equatorial orbit = very long traverse. May need
   to orbit into a higher inclination. Future problem.

3. **PlanetRadius** -- always from status.json live. Not stored in waypoint.

4. **Terrain avoidance post-glide** -- status.json Altitude is MSL above
   mean radius, not above terrain. On rough worlds this matters.
   v1: maintain 500m minimum alt, ignore terrain.

5. **ApproachSettlement timing** -- does it fire in OC or only in normal space?
   If OC: can use as lat/lon source. If only normal space: too late for nav.
