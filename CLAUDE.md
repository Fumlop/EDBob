# EDBob Project Rules

## Screen Capture

`mss.grab` returns BGRA. All screen capture functions return raw BGRA -- no channel
swapping. OpenCV treats this as BGR with alpha, which is correct for `COLOR_BGR2HSV`
and all color detection.

## Paint Testing

Before changing any screen region config, always:
1. Paint the old and new box on a screenshot
2. Show raw crop and HSV mask
3. Print pixel stats (H/S/V ranges, match percentage)
