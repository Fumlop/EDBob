# EDAPGui Project Rules

## Screen Capture: Always use inv_col=False

`mss.grab` returns BGRA. The `get_screen_region(reg, rgb=True)` path does a bogus
`COLOR_RGB2BGR` swap that corrupts channel order. This halves orange detection and
completely kills cyan detection (0% match).

**Rule:** All `capture_region` and `capture_region_filtered` calls MUST use `inv_col=False`.

When testing screen regions on static screenshots (Paint tests), always test BOTH paths
to verify color filters work correctly:
- `inv_col=False` = correct BGR from mss
- `inv_col=True` = swapped channels (broken)

## Paint Testing

Before changing any screen region config, always:
1. Paint the old and new box on a screenshot
2. Show raw crop and HSV mask
3. Print pixel stats (H/S/V ranges, match percentage)
4. Test with both inv_col paths
