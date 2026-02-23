"""
Application-wide constants for EDBob (Boring Operations Bot).
Single source of truth -- import from here, don't redefine elsewhere.
"""

# Application version
EDAP_VERSION = "V1.9.0 b4"

# GUI form field types
FORM_TYPE_CHECKBOX = 0
FORM_TYPE_SPINBOX = 1
FORM_TYPE_ENTRY = 2

# Elite Dangerous window title (used for focus detection and overlay)
ED_WINDOW_TITLE = "Elite - Dangerous (CLIENT)"

# Galaxy map favorites list region in percent [L, T, R, B]
FAV_LIST_REGION_PCT = [0.076, 0.172, 0.215, 0.522]
