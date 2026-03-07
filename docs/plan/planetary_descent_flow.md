# Planetary Descent Flow

Updated with lessons from test_oc_nav.py (session 2026-02-26).

## Trigger: SC Assist active, waypoint has IsPlanetary=true + Latitude + Longitude

```
SC_ASSIST (existing)
    |
    v
[SPA] WAIT FOR OC FLAGS
    |  - SC Assist approaches the body and enters orbit
    |  - OC flags: FlagsSupercruise + FlagsHasLatLong + FlagsAverageAltitude
    |  - These can fire early (~990km) -- use ApproachBody journal event as
    |    a more reliable "real OC" trigger
    |  - At OC detection: start reading Lat/Lon/Alt/Heading from status.json
    |
    v
[SPA] CONFIRM ORBIT (stable alt check)
    |  - Poll altitude every status.json cycle
    |  - CONFIRMED when: alt drift < 10% for 10 continuous seconds
    |  - If drift > 10%: reset timer, wait again
    |  - Orientation after orbit: belly-down (top-down), canopy toward planet
    |    This is guaranteed by SC Assist -- do NOT act before orbit confirmed
    |
    v
[OED] WAIT FOR DIVE WINDOW (heading + angle)
    |  - Compute bearing to settlement: bearing_to(lat, lon, tgt_lat, tgt_lon)
    |  - Compute dist_3d: straight-line distance ship->target (not surface arc)
    |  - Compute glideslope_angle = atan2(alt, dist_3d)
    |
    |  IMPORTANT -- glideslope_angle is NOT the ship's pitch angle.
    |  It is the geometric elevation angle: angle at the target between
    |  the surface plane and the line from target up to the ship.
    |  0 deg = ship on the horizon, 90 deg = ship directly overhead.
    |  Use it to decide WHEN to dive, not HOW MUCH to pitch.
    |
    |  - Heading aligned: |heading_diff(heading, bearing)| < 3 deg
    |  - Dive window: 35 <= glideslope_angle <= 38 AND dist/alt <= 2.0
    |  - While waiting: DO NOT yaw -- orbit naturally brings target into view
    |    (active yaw in OC with no SC Assist was unreliable in tests)
    |
    v
[DIVE] DIVE INITIATE
    |  - Lock the glideslope_angle at trigger: lock_angle = glideslope_angle
    |  - Throttle zero (LeftShift)
    |  - Pitch +45 deg toward planet
    |  - Poll altitude: when alt drops to 60% of entry alt, pitch -45 deg (pullback)
    |  - Timeout 30s on the poll
    |
    v
[DIVE] DIVE CORRECT (maintain locked angle + steer)
    |  - Every status cycle compute current glideslope_angle = atan2(alt, dist_3d)
    |  - Maintain lock_angle +/- 0.4 deg band:
    |      above band (too shallow): pitch toward planet
    |      below band (too steep): pitch away from planet
    |  - Correct heading: yaw if |hdg_err| > 2 deg
    |  - Continue until Flags2GlideMode fires
    |
    |  KNOWN PROBLEM -- glideslope feedback loop does NOT work in OC:
    |  - Ship pitched ~80 deg toward planet (visually)
    |  - glideslope stayed at ~40 deg, never reached lock_angle=35 deg
    |  - ED does not simulate real orbital mechanics -- no gravity pull at speed.
    |    Ship moves in direction it points (with lag), throttle zero = ~30 km/s.
    |  - Likely cause: heading was off-target during dive, ship flying past
    |    settlement at 30 km/s -> dist_3d grew -> glideslope stayed high.
    |    OR: pitch pulses too short, game needs sustained hold to change alt.
    |  - Confirmed: reactive pitch correction loop produced wrong results.
    |  - Unknown: whether root is heading drift, pitch lag, or both.
    |    -> PlanetaryTracker data needed to diagnose.
    |  HARD CONSTRAINT: throttle zero in OC = still ~30 km/s.
    |    Orbital velocity cannot be bled -- "wait for nose/velocity alignment"
    |    is not viable in any timeframe before glide engages.
    |  TODO v1: align heading BEFORE dive, then commit to fixed pitch angle
    |           and hold it. No correction loop. glideslope_angle = trigger only.
    |
    v
GLIDE (passive, ~10-15s)
    |  - Detection: Flags2GlideMode
    |  - Hold current attitude, do not fight it
    |  - Alt drops ~20km -> ~4km
    |  - Aggressive yaw = pilot blackout (avoid)
    |  - Exits ~3-5km from settlement (from run data)
    |
    v
POST-GLIDE APPROACH
    |  - Detection: NOT FlagsSupercruise + FlagsHasLatLong + NOT Flags2GlideMode
    |  - Compass points at settlement -- use existing alignment code
    |  - Fly toward settlement, maintain minimum altitude
    |  - Request docking when in range
    |
    v
DOCKING (existing code)
```

## Data Sources Per Phase

| Phase | Primary Nav | Notes |
|-------|------------|-------|
| SC Approach | Compass (existing) | -- |
| OC Wait | status.json flags | ApproachBody journal = reliable trigger |
| Orbit Confirm | status.json Altitude | 10s stable, 10% tolerance |
| Heading Align | status.json Heading + bearing_to() | Only after SC Assist off |
| Dive Window | glideslope_angle = atan2(alt, dist_3d) | NOT ship pitch |
| Dive Correct | glideslope_angle + heading_diff | lock angle at trigger |
| Glide | Passive | Flags2GlideMode |
| Post-Glide | Compass (existing) | -- |
| Docking | Existing docking code | -- |

## Key Formulas

### Phase detection
```python
# src/ed/EDNavUtils.py
phase = detect_phase(flags, flags2)   # -> "OC", "GLIDE", "SC", etc.
is_orbiting(flags, flags2)            # -> True in OC
```

### Surface distance (meters)
```python
haversine_distance(ship_lat, ship_lon, target_lat, target_lon, planet_radius)
```

### Bearing to target (degrees, 0=N)
```python
bearing_to(ship_lat, ship_lon, target_lat, target_lon)
```

### Heading error (signed, +R -L)
```python
heading_diff(current_heading, bearing)
```

### Approach angle -- WHEN to dive (NOT ship pitch)
```python
# glideslope_angle is the angle at the TARGET looking up to the ship.
# 35-38 deg = good dive window (ship is ahead and high enough)
d3 = dist_3d(lat, lon, alt, tgt_lat, tgt_lon, planet_r)
angle = glideslope_angle(alt, d3)   # atan2(alt, d3), degrees
```

### Dive trigger condition
```python
ratio = dist_3d / alt
if 35.0 <= glideslope_angle <= 38.0 and ratio <= 2.0 and heading_aligned:
    start_dive(lock_angle=glideslope_angle)
```

### Dive angle maintenance
```python
# After initiate: lock angle at trigger. Each cycle:
current_angle = glideslope_angle(alt, dist_3d(lat, lon, alt, tgt_lat, tgt_lon, planet_r))
error = current_angle - lock_angle   # + = too shallow, - = too steep
# Correct pitch: +pitch toward planet if too shallow, -pitch if too steep
```

## Orbit Detection Detail

```
orbit_check_alt = current_alt
orbit_check_start = now()

each cycle:
    drift = abs(alt - orbit_check_alt) / orbit_check_alt
    if drift > 0.10:           # 10% tolerance
        orbit_check_alt = alt  # reset
        orbit_check_start = now()
    elif elapsed >= 10.0:      # 10s stable
        ORBIT CONFIRMED
```

## Known Issues / TODO

- [ ] Heading alignment during OC (post SC Assist off) -- orbit naturally
      carries us, need to decide: wait for orbit to bring bearing into view
      vs. active yaw. Active yaw in tests was unreliable. Passive wait TBD.
- [ ] SC Assist deactivation via nav panel -- same method as activation
- [ ] ApproachBody journal event integration
- [ ] Post-glide distance varies (3-5km from run data) -- compass handles this
- [ ] Polar settlements: auto-orbit near equator means long traverse
- [ ] Settlement lat/lon: from waypoint IsPlanetary fields (see example_planetary.json)
- [ ] PlanetRadius in waypoint (optional) -- StatusParser provides it live

## Test Data

### Target: Voelundr Hub (test reference)
- Lat=57.8973, Lon=171.3885
- PlanetRadius=1,148,728m (1.15 Mm)
- Heading on pad: 238

### Run01 (manual, no target tracking)
- Start: Lat=34.20, Lon=-60.96, Alt=70km (already in OC)
- Glide entry: Alt=20.3km, Lat=58.49, Lon=172.66
- Post-glide: 3.8km from settlement
- Total OC time: 91s

### Run02 (manual, CSV logged)
- Start: Lat=-27.34, Lon=103.67, Alt=851km (very high OC entry)
- Glide entry: Alt=22.3km, Lat=58.69, Lon=174.05
- Post-glide: 4.6km from settlement
- Total OC time: 106s
- Descent from 95km->22km took ~22s, alt_rate -1300 to -10500 m/s
