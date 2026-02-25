# Planetary Settlement Approach -- Implementation Plan

## Problem Statement

SC Assist does NOT land on planets. It only orbits. The current EDAP code
actually *evades* when `ApproachBody` fires. For planetary settlements and
construction depots on moons/planets, we need a fully autonomous descent
sequence.

## Current Hauling Target

Beadohild Point (SpaceConstructionDepot) on Hyades Sector GW-V c2-4 A 2 a
(a moon). Currently reached via SC Assist which drops us at orbital stations
only. This settlement requires planetary approach.

---

## Flight Phases

```
Deep SC ──> Pre-Orbital Align ──> Orbital Cruise ──> Glide ──> Normal Space ──> Dock
   |              |                    |               |            |             |
 existing    HARDEST PART          pitch down       maintain     fly to base   existing
 compass     (see below)           ~45 deg          safe zone    via compass   docking
```

## Phase Breakdown

### Phase 0: Deep SC Approach (EXISTING)

What works today: compass align, SC toward target. The compass points at the
settlement which is on the planet surface.

**Problem**: Following the compass straight in points us AT the planet surface.
We'd arrive at the orbital boundary aimed almost horizontally at the planet,
or worse, aimed at the planet core. This gives us a bad entry angle for glide.

### Phase 1: Pre-Orbital Alignment (HARDEST PART)

**Why this is hard:**

The settlement is on the surface. The compass points at it. But we need to
arrive at the orbital boundary (~25km altitude) positioned ABOVE the settlement,
not aimed directly at it. Then we pitch down 45 degrees into glide.

If we follow the compass blindly:
- We approach the planet aimed at the surface
- We enter orbital cruise at a random angle relative to the settlement
- We'd need to orbit around to reposition -- slow and complex

**What we actually need:**

Approach the planet so that when we cross the orbital boundary, the settlement
is roughly 25km below us and slightly ahead. This means we need to aim NOT at
the settlement itself, but at a point ~25km above it.

**Possible strategies:**

#### Strategy A: "Overshoot and Orbit"
1. Follow compass toward settlement (existing alignment)
2. SC Assist takes us to orbital cruise (it orbits the planet)
3. In orbital cruise: read Lat/Lon/Heading from status.json
4. Navigate in orbital cruise until we're above the settlement
5. Pitch down 45 degrees into glide

Pros: Simple, uses existing SC Assist code
Cons: Orbiting to find the right position is slow, need orbital cruise nav

#### Strategy B: "Offset Approach"
1. Align to compass (settlement direction)
2. Before entering orbital zone, pitch up ~20-30 degrees from compass center
3. This makes us arrive at the orbital boundary above the settlement
4. Immediately pitch down 45 degrees into glide

Pros: Fast, direct approach
Cons: Tricky to calculate the right offset angle. Depends on approach distance.

#### Strategy C: "Let SC Assist Orbit, Then Dive" (RECOMMENDED for v1)
1. Approach planet normally (SC Assist or compass align)
2. When `ApproachBody` fires + `FlagsHasLatLong` set = orbital cruise
3. Instead of evading: read status.json for Lat/Lon/Alt/Heading
4. Compute bearing to settlement from current position
5. Align heading to settlement bearing
6. Pitch down 45 degrees
7. Enter glide

Pros: Most data-driven, uses status.json numbers not screen reading
Cons: Need to compute great-circle bearing, handle "settlement on far side"

**Decision**: Strategy C is most robust. Status.json gives us real navigation
data. No guessing about screen positions.

### Phase 2: Orbital Cruise Navigation

**Detection**: `FlagsSupercruise AND FlagsHasLatLong`

**Available data from status.json:**
- `Latitude` (float, degrees)
- `Longitude` (float, degrees)
- `Heading` (int, degrees bearing)
- `Altitude` (float, meters)
- `PlanetRadius` (float, meters)

**From journal `ApproachSettlement` event:**
- Settlement `Latitude` and `Longitude`

**Navigation algorithm:**
1. Read current Lat/Lon and settlement Lat/Lon
2. Compute great-circle bearing: `bearing = atan2(sin(dLon)*cos(lat2), cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(dLon))`
3. Compare with current `Heading`
4. Yaw to match bearing
5. Pitch down to ~45 degrees
6. Monitor altitude -- glide engages at ~25km

**Orbital cruise controls:**
- Pitch 0 = maintain altitude (circle planet)
- Pitch down = descend
- Pitch up = ascend
- Speed: throttle in blue zone for max orbital speed

### Phase 3: Glide

**Detection**: `Flags2GlideMode` (already have this)

**What we need:**
- Currently we just `wait_for_flag2_off(Flags2GlideMode, 30)` -- passive wait
- Should actively manage pitch to stay in safe zone
- Monitor altitude via status.json (decreasing from ~25km to ~3km)
- Keep heading toward settlement (minimal yaw -- aggressive yaw causes blackout)

**Glide rules:**
- Entry angle: -5 to -60 degrees (optimal: -40 to -50)
- Speed: fixed 2,500 m/s
- Too steep pitch = emergency drop (hull damage)
- Too shallow = early exit (far from target)
- Aggressive yaw = pilot blackout

**For v1**: Keep passive wait. The glide is short (~10-15 seconds) and if our
entry angle was ~45 degrees, the default glide should deposit us close enough.

### Phase 4: Normal Space to Settlement

**Detection**: NOT `FlagsSupercruise` AND NOT `Flags2GlideMode` AND `FlagsHasLatLong`

**Navigation:**
- Use compass (points at settlement) -- existing alignment code
- Fly toward settlement at moderate speed
- `ApproachSettlement` journal event fires when close
- Request docking when in range
- Deploy landing gear
- Existing docking code may partially work (station services)

**Concerns:**
- Post-glide distance could be 0-50km depending on glide accuracy
- Gravity varies per planet -- high-G worlds need careful throttle
- Need to manage altitude (don't crash into terrain)

---

## Data Sources Summary

| Data | Source | Reliability |
|------|--------|-------------|
| In orbital cruise? | status.json: Supercruise + HasLatLong | High |
| In glide? | status.json: Flags2GlideMode | High |
| Current position | status.json: Lat/Lon/Alt/Heading | High |
| Settlement position | Journal: ApproachSettlement Lat/Lon | High |
| Compass direction | Screen: existing navball detection | Medium |
| Pitch angle | Computed from altitude rate or compass | Medium |
| Distance to settlement | Computed from Lat/Lon + great-circle | High |

Key insight: **status.json gives us real navigation data** (lat, lon, heading,
altitude). This is more reliable than screen reading for planetary navigation.
The compass is a backup/verification, not the primary nav source.

---

## Implementation Order

### Step 1: Parse ApproachSettlement journal event
- Add handler in EDJournal.py
- Store settlement name, lat, lon in ship state
- Small change, no risk

### Step 2: Detect orbital cruise state
- Add check: `FlagsSupercruise AND FlagsHasLatLong`
- In `supercruise_to_station()`: branch to planetary descent when target
  is a settlement (not an orbital station)
- Need to know if target is planetary -- journal `FSDTarget` or
  `ApproachBody` + `ApproachSettlement` combo

### Step 3: Orbital cruise navigation
- Read status.json Lat/Lon/Heading/Altitude
- Compute bearing to settlement
- Yaw to correct heading
- Pitch down 45 degrees
- Monitor altitude for glide entry

### Step 4: Glide management (v1: passive)
- Keep existing `wait_for_flag2_off(Flags2GlideMode, 30)`
- Later: active pitch management for accuracy

### Step 5: Post-glide approach
- Detect normal space near planet
- Compass align to settlement
- Fly toward it
- Request docking + land

---

## TODO

- [ ] User needs to fill in real Lat/Lon coords for Beadohild Point
      (manual visit or lookup from EDSM/Inara, check journal ApproachSettlement)
- [ ] Example waypoint file created at `waypoints/example_planetary.json`
      with IsPlanetary/Latitude/Longitude fields -- not wired into code yet
- [ ] Come back to planetary descent implementation after hauling loop stabilises

## Open Questions

1. **How do we know the target is a planetary settlement vs orbital station?**
   - Journal `Docked`/`Location` events have `StationType` field
   - `SpaceConstructionDepot` on a planet = planetary
   - Could also check if `ApproachBody` fires before SC drop
   - Or: if we enter orbital cruise while targeting a station, it's planetary

2. **Settlement on far side of planet?**
   - Need to orbit in orbital cruise until above it
   - Great-circle distance tells us how far to go

3. **Terrain avoidance in normal space?**
   - Status.json `Altitude` is our friend
   - Maintain minimum altitude while approaching

4. **Variable gravity handling?**
   - Can read gravity from system data or infer from descent rate
   - For v1: conservative throttle management

5. **Pre-orbital alignment -- can we skip orbiting?**
   - If we approach from the right direction, we can dive straight in
   - Requires knowing settlement lat/lon BEFORE entering orbit
   - `ApproachSettlement` may fire too late (only in normal space?)
   - May need to get lat/lon from nav panel or system map

---

## Pre-Orbital Alignment Deep Dive (THE HARD PART)

The fundamental geometry problem:

```
        Ship approaching from deep space
             \
              \  (SC direction)
               \
                v
    ========== Orbital Boundary (~25km) ==========
                |
                | (need ~45 deg dive here)
                |
           Settlement on surface
```

If we approach with compass centered (aimed at settlement), we hit the
orbital boundary aimed almost horizontally at the planet face. We need to
be ABOVE the settlement when we cross the boundary.

**The geometry:**
- Planet radius R (from status.json `PlanetRadius`)
- Orbital boundary at R + 25km
- Settlement at lat/lon on surface
- We need to cross the boundary at a point ~25km horizontal distance
  from the settlement (at 45 deg, vertical 25km = horizontal 25km)

**Option 1: Don't solve it pre-orbit**
Just enter orbital cruise however we arrive. Then navigate in orbital cruise
to position above settlement. This is Strategy C above -- simplest to implement,
slightly slower in practice.

**Option 2: Compass offset**
When approaching in SC, the compass points at the settlement. The planet's
center is "behind" the settlement from our perspective. If we aim slightly
above the compass dot (toward planet edge), we arrive at the orbital boundary
above the settlement. The offset angle depends on distance and planet size.

At long range: compass dot = settlement direction = planet direction (they
overlap). As we get closer, they diverge. The planet fills more of the view.
The settlement dot stays on the planet face but the "above settlement" point
moves toward the planet's limb.

This is hard to compute from screen data alone. Status.json approach is better.

**Recommendation: Strategy C (orbit then dive) for v1.**
Optimize pre-orbital approach angle in v2 once we have orbital cruise working.
