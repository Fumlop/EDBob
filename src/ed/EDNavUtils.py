"""
Planetary navigation utilities.

Phase detection and geodetic calculations used during Orbital Cruise
and planetary approach.
"""

import math

from src.core.EDAP_data import (
    FlagsDocked, FlagsLanded, FlagsSupercruise, FlagsHasLatLong,
    FlagsAverageAltitude, FlagsFsdJump,
    Flags2GlideMode,
)


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------

PHASE_GLIDE = "GLIDE"
PHASE_DOCKED = "DOCKED"
PHASE_LANDED = "LANDED"
PHASE_HYPERSPACE = "HYPERSPACE"
PHASE_OC = "OC"               # Orbital Cruise -- supercruise + lat/lon + average alt
PHASE_SC_NEAR = "SC_NEAR"     # Supercruise near planet (lat/lon visible, no avg alt)
PHASE_SC = "SC"               # Normal supercruise
PHASE_NORMAL_PLANET = "NORMAL_PLANET"  # Normal flight near planet (lat/lon visible)
PHASE_NORMAL = "NORMAL"


def detect_phase(flags: int, flags2: int | None) -> str:
    """Classify current flight phase from status flags.

    Returns one of the PHASE_* constants defined in this module.

    Priority order matters -- glide and docked/landed are checked first.
    """
    if (flags2 or 0) & Flags2GlideMode:
        return PHASE_GLIDE
    if flags & FlagsDocked:
        return PHASE_DOCKED
    if flags & FlagsLanded:
        return PHASE_LANDED
    if flags & FlagsFsdJump:
        return PHASE_HYPERSPACE
    if flags & FlagsSupercruise:
        if flags & FlagsHasLatLong:
            if flags & FlagsAverageAltitude:
                return PHASE_OC
            return PHASE_SC_NEAR
        return PHASE_SC
    if flags & FlagsHasLatLong:
        return PHASE_NORMAL_PLANET
    return PHASE_NORMAL


def is_orbiting(flags: int, flags2: int) -> bool:
    """Return True when in Orbital Cruise (supercruise with altitude indicator)."""
    return detect_phase(flags, flags2) == PHASE_OC


def is_above_planet(flags: int, flags2: int) -> bool:
    """Return True when lat/lon data is available (OC, SC_NEAR, or normal near planet)."""
    return bool(flags & FlagsHasLatLong)


# ---------------------------------------------------------------------------
# Geodetic calculations
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float, radius_m: float) -> float:
    """Great-circle surface distance in meters between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius_m * 2 * math.asin(math.sqrt(a))


def bearing_to(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Forward bearing in degrees (0=N, 90=E, clockwise) from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360


def dist_3d(lat1: float, lon1: float, alt: float, lat2: float, lon2: float, radius_m: float) -> float:
    """Straight-line 3D distance from ship (at altitude above surface) to a surface target."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    r_ship = radius_m + alt
    sx = r_ship * math.cos(lat1) * math.cos(lon1)
    sy = r_ship * math.cos(lat1) * math.sin(lon1)
    sz = r_ship * math.sin(lat1)
    tx = radius_m * math.cos(lat2) * math.cos(lon2)
    ty = radius_m * math.cos(lat2) * math.sin(lon2)
    tz = radius_m * math.sin(lat2)
    return math.sqrt((sx - tx) ** 2 + (sy - ty) ** 2 + (sz - tz) ** 2)


def heading_diff(current: float, target: float) -> float:
    """Signed heading error in degrees: positive = turn right, negative = turn left."""
    return (target - current + 180) % 360 - 180


def glideslope_angle(alt: float, d3: float) -> float:
    """Glideslope beam angle from surface target up to ship, in degrees.

    Mirrors ILS geometry: transmitter (target) on surface projects a beam
    upward at an angle -- we ride that beam down to the target.

    IMPORTANT: this is NOT the ship's pitch/alignment angle.
    It is the angle at the target between the surface plane and the line to the ship.
    atan2(alt, dist_3d) -- 0 deg = ship on horizon, 90 deg = ship directly overhead.
    Use this to decide WHEN to dive, not HOW MUCH to pitch.
    """
    if d3 <= 0 or alt <= 0:
        return 90.0
    return math.degrees(math.atan2(alt, d3))
