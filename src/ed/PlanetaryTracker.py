"""
PlanetaryTracker -- passive CSV logger for planetary approach analysis.

Logs all status.json fields plus derived nav values every status tick.
Stops automatically on DOCKED or LANDED.

Standalone usage (hardcoded test target):
    python -m src.ed.PlanetaryTracker

Embed usage:
    tracker = PlanetaryTracker(status, target_lat=57.8973, target_lon=171.3885)
    tracker.start()
    ...
    tracker.stop()
"""

import csv
import os
import threading
from datetime import datetime

from src.ed.StatusParser import StatusParser
from src.ed.EDNavUtils import (
    detect_phase, PHASE_DOCKED, PHASE_LANDED,
    bearing_to, haversine_distance, dist_3d, glideslope_angle, heading_diff,
)

OUTPUT_DIR = "debug-output/planetary"

# Test target: Voelundr Hub
TEST_TARGET_LAT = 57.8973
TEST_TARGET_LON = 171.3885

CSV_COLUMNS = [
    "timestamp", "phase",
    "lat", "lon", "alt", "heading", "planet_r",
    "flags", "flags2",
    "bearing", "dist_surface", "dist_3d", "glideslope_deg", "hdg_err",
]


class PlanetaryTracker:
    def __init__(self, status: StatusParser, target_lat: float, target_lon: float):
        self.status = status
        self.target_lat = target_lat
        self.target_lon = target_lon
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.log_path: str | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PlanetaryTracker")
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts_start = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(OUTPUT_DIR, f"track_{ts_start}.csv")

        print(f"[PlanetaryTracker] logging to {self.log_path}")
        print(f"[PlanetaryTracker] target lat={self.target_lat} lon={self.target_lon}")
        print(f"[PlanetaryTracker] stops on DOCKED or LANDED -- Ctrl+C to abort")

        with open(self.log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            last_ts = None
            while not self._stop_event.is_set():
                # Block until status.json changes (up to 2s)
                self.status.wait_for_file_change(last_ts or "", timeout=2)
                d = self.status.get_cleaned_data()
                if d is None:
                    continue

                ts = d.get("timestamp", "")
                if ts == last_ts:
                    continue
                last_ts = ts

                flags = d["Flags"]
                flags2 = d["Flags2"] or 0
                phase = detect_phase(flags, flags2)

                lat = d["Latitude"]
                lon = d["Longitude"]
                alt = d["Altitude"]
                hdg = d["Heading"]
                planet_r = d["PlanetRadius"]

                # Derived nav values -- only when we have position data
                brg = dist_s = d3 = gs = hdg_e = ""
                if lat is not None and lon is not None and planet_r:
                    brg = round(bearing_to(lat, lon, self.target_lat, self.target_lon), 2)
                    dist_s = round(haversine_distance(lat, lon, self.target_lat, self.target_lon, planet_r), 0)
                    if alt is not None:
                        d3_val = dist_3d(lat, lon, alt, self.target_lat, self.target_lon, planet_r)
                        d3 = round(d3_val, 0)
                        gs = round(glideslope_angle(alt, d3_val), 2)
                    if hdg is not None:
                        hdg_e = round(heading_diff(hdg, brg), 2)

                row = {
                    "timestamp": ts,
                    "phase": phase,
                    "lat": lat,
                    "lon": lon,
                    "alt": alt,
                    "heading": hdg,
                    "planet_r": planet_r,
                    "flags": flags,
                    "flags2": flags2,
                    "bearing": brg,
                    "dist_surface": dist_s,
                    "dist_3d": d3,
                    "glideslope_deg": gs,
                    "hdg_err": hdg_e,
                }
                writer.writerow(row)
                f.flush()

                print(
                    f"[{ts}] {phase:<16}  "
                    f"alt={_fmt(alt)}  "
                    f"gs={gs if gs != '' else 'N/A':>6}  "
                    f"hdg_err={hdg_e if hdg_e != '' else 'N/A':>7}  "
                    f"dist={_fmt(dist_s)}"
                )

                if phase in (PHASE_DOCKED, PHASE_LANDED):
                    print(f"[PlanetaryTracker] {phase} -- stopping.")
                    break

        print(f"[PlanetaryTracker] saved: {self.log_path}")


def _fmt(m) -> str:
    if m == "" or m is None:
        return "N/A"
    m = float(m)
    if m >= 1_000_000:
        return f"{m / 1_000_000:.2f}Mm"
    if m >= 1_000:
        return f"{m / 1_000:.1f}km"
    return f"{m:.0f}m"


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    status = StatusParser()
    tracker = PlanetaryTracker(status, TEST_TARGET_LAT, TEST_TARGET_LON)
    tracker.start()
    try:
        while tracker._thread.is_alive():
            tracker._thread.join(timeout=0.5)
    except KeyboardInterrupt:
        tracker.stop()
        tracker._thread.join(timeout=3)
        print("\n[PlanetaryTracker] aborted by user")
