# EDShipControl.py -- Ship Control Interface

## Purpose

Thin wrapper for ship control operations. Delegates to `MenuNav` for all menu key sequences.
Lives in `src/ed/EDShipControl.py`.

## Class: EDShipControl

### Constructor

| Parameter | Type | Description |
|---|---|---|
| `ed_ap` | EDAutopilot | Parent autopilot instance (provides `ocr`) |
| `screen` | Screen | Screen capture instance |
| `keys` | EDKeys | Key sending interface |
| `cb` | callable | GUI callback `cb(msg, body)` |

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `ocr` | OCR | OCR instance from ed_ap |
| `screen` | Screen | Screen capture |
| `keys` | EDKeys | Key sender |
| `status_parser` | StatusParser | Status.json reader |
| `ap_ckb` | callable | GUI callback |

### Methods

| Method | Returns | Description |
|---|---|---|
| `goto_cockpit_view()` | bool | Delegates to `MenuNav.goto_cockpit()`. Returns True once in cockpit view (all panels closed). |

## Dependencies

| Module | Purpose |
|---|---|
| `MenuNav` | All menu key sequences delegated here |
| `StatusParser` | Monitors GUI focus state |
| `EDAP_data` | Global constants (unused directly, used via StatusParser) |

## Notes

- Single method class, actual key logic lives in `MenuNav.goto_cockpit()`
- Can be extended for additional ship control operations
