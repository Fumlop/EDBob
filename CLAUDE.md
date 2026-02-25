# EDBob Project Rules

## Screen Capture

`mss.grab` returns BGRA. All screen capture functions return raw BGRA -- no channel
swapping. OpenCV treats this as BGR with alpha, which is correct for `COLOR_BGR2HSV`
and all color detection.

## Navball Geometry

The navball is an orthographic sphere projection. `_calc_nav_angles()` uses
`asin()` to convert dot position to degrees -- this is correct. Do NOT change
to linear mapping. Minor yaw coupling at large pitch is irrelevant due to
iterative alignment. See `docs/src/ED_AP.md` for full analysis.

## Paint Testing

Before changing any screen region config, always:
1. Paint the old and new box on a screenshot
2. Show raw crop and HSV mask
3. Print pixel stats (H/S/V ranges, match percentage)
