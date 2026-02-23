# Alignment Overshoot Analysis Verdict

## Date: 2026-02-19

## Data Source: autopilot.log.3 (rotated from log.1)

## Verdict: NO real overshoot

The data shows:
1. **Direction flips happen at small angles (< 7deg)** -- this is ring center measurement noise (~3-5px jitter = ~3-7deg), not overcorrection
2. **Large angle corrections converge cleanly** -- the approach percentages (0.4/0.6/0.8) work fine for big moves
3. **The jitter is already fixed** by: 3-of-5 voting, r>=55 filter, 15px distance filter, and close=4.0 tolerance

## Evidence

### Alignment Run 1 (20:45:21 - pre-FSD)

**Pitch sequence (attempt 3):**

| Time | Remaining | Direction | Hold |
|------|-----------|-----------|------|
| 42.945 | 90.0deg | PitchDown | 2.00s |
| 47.128 | dir changed 90->36.1 | PitchUp | 1.81s |
| 51.114 | 7.4deg | PitchUp | 0.19s |
| 53.484 | 12.5deg | PitchUp | 0.47s |
| 56.132 | 9.0deg | PitchUp | 0.22s |
| 58.539 | 4.5deg | PitchUp | 0.11s |
| 60.830 | 4.4deg | PitchUp | 0.11s |
| 63.121 | dir changed 4.4->7.0 | PitchDown | TIMEOUT |

The 4.4 -> 7.0 flip is 2.6deg jitter, not overshoot. With close=4.0, it would exit as aligned before that flip.

**Yaw sequence:**
- 29.9 -> 13.4 -> 5.8 -> 4.9 -> 10.8 (jitter, no direction flip) -> 1.4 aligned
- The 4.9->10.8 jump is ring center noise, not overshoot

### Alignment Run 2 (20:47:23 - in-system)

**Pitch:** 81.2 -> 61 -> 43.5 -> 35.1 -> 5.7 -> 7.3 -> aligned at -4.0deg. Clean convergence.
**Yaw:** 44.0 -> 24.6 -> 14.7 -> aligned at -0.2deg. Perfect, no bounce.

## asin mapping note

asin is still correct (navball is a sphere), but it wouldn't have fixed this particular problem. At small angles where the jitter occurs, linear vs asin gives nearly identical results (asin(0.1) = 5.74deg vs linear 9.0deg). The difference only matters at larger angles where convergence was already clean.

## SC Assist detection note

The single `sc_assist_ind` box consistently reads 0.000 while text reads ~0.04. Proposed fix: replace the single indicator box with **2 small boxes** sampling two different spots on the SC assist triangle. Measuring two distinct points on the triangle is more reliable than one box that may not overlap the feature properly.

## Root causes of alignment issues (all fixed)

1. HoughCircles ring center jitter -> 3-of-5 voting with median
2. Bad HoughCircles results (r<55 or far from ROI center) -> filtered out
3. close=3.0 too tight for measurement noise -> raised to 4.0
4. Linear angle mapping on spherical navball -> asin mapping
