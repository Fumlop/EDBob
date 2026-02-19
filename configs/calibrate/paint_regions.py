"""Paint screen region rects on a reference screenshot for visual calibration.

Usage:
    python configs/calibrate/paint_regions.py              # all regions
    python configs/calibrate/paint_regions.py compass      # single region
    python configs/calibrate/paint_regions.py compass sun  # multiple regions

Config:
    Edit the paths below to match your setup.
"""
import cv2
import json
import sys
import os

# --- Config: edit these ---
SCREENSHOT = os.path.join(os.path.dirname(__file__), 'reference_1920x1080.png')
REGIONS_JSON = os.path.join(os.path.dirname(__file__), '..', 'screen_regions', 'res_1920_1080', 'default.json')
OUTPUT = os.path.join(os.path.dirname(__file__), 'regions_overlay.png')
# --------------------------

COLORS = [
    (0, 255, 0),     # green
    (0, 255, 255),    # yellow
    (255, 0, 255),    # magenta
    (255, 128, 0),    # blue-ish
    (0, 165, 255),    # orange
    (128, 255, 128),  # light green
    (200, 200, 200),  # gray
]

img = cv2.imread(SCREENSHOT)
if img is None:
    print(f"Failed to load screenshot: {SCREENSHOT}")
    sys.exit(1)

with open(REGIONS_JSON) as f:
    config = json.load(f)

regions = config['regions']
names = sys.argv[1:] if len(sys.argv) > 1 else list(regions.keys())

for i, name in enumerate(names):
    if name not in regions:
        print(f"Unknown region '{name}', available: {list(regions.keys())}")
        continue
    x1, y1, x2, y2 = regions[name]['rect']
    color = COLORS[i % len(COLORS)]
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    w, h = x2 - x1, y2 - y1
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.drawMarker(img, (cx, cy), color, cv2.MARKER_CROSS, 10, 1)
    label = f"{name} [{x1},{y1},{x2},{y2}] {w}x{h}"
    cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    print(f"{name}: [{x1}, {y1}, {x2}, {y2}]  center=({cx},{cy})  {w}x{h}px")

cv2.imwrite(OUTPUT, img)
print(f"\nSaved to {OUTPUT}")
