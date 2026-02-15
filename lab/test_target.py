"""
Test script: Target reticle detection accuracy test.
Takes screenshots and tests template matching for the target circle.
Run while in supercruise with a nav target selected and roughly aligned.

Usage: python -m lab.test_target
"""
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from numpy import array
from src.screen.Screen import Screen, set_focus_elite_window
from src.screen.Screen_Regions import Screen_Regions
from src.screen.Image_Templates import Image_Templates


def dummy_cb(*args):
    pass


def init_screen():
    """Initialize screen capture and templates."""
    scr = Screen(dummy_cb)
    print(f"Screen: {scr.screen_width}x{scr.screen_height} at ({scr.screen_left},{scr.screen_top})")
    print(f"Scale: X={scr.scaleX:.3f} Y={scr.scaleY:.3f}")

    # Load templates with same scaling as EDAP
    templ = Image_Templates(scr.scaleX, scr.scaleY, scr.scaleX, scr.scaleX)
    scr_reg = Screen_Regions(scr, templ)
    return scr, scr_reg, templ


def test_target_detection(scr, scr_reg, templ):
    """Capture target region and test template matching."""
    ts = time.strftime("%H%M%S")

    # Grab the target region (filtered by orange color)
    target_filtered = scr_reg.capture_region_filtered(scr, 'target', inv_col=True)
    target_occ_filtered = scr_reg.capture_region_filtered(scr, 'target_occluded', inv_col=False)

    # Also grab raw (unfiltered) for visual inspection
    target_rect = scr_reg.reg['target']['rect']
    target_raw = scr.get_screen_rect_pct(target_rect)

    # Save images
    cv2.imwrite(f"lab/target_{ts}_raw.png", target_raw)
    cv2.imwrite(f"lab/target_{ts}_filtered.png", target_filtered)
    print(f"  Saved: lab/target_{ts}_raw.png ({target_raw.shape})")
    print(f"  Saved: lab/target_{ts}_filtered.png ({target_filtered.shape})")

    # Template info
    tgt_templ = templ.template['target']['image']
    tgt_occ_templ = templ.template['target_occluded']['image']
    print(f"  Target template size: {tgt_templ.shape}")
    print(f"  Target occluded template size: {tgt_occ_templ.shape}")
    print(f"  Filtered region size: {target_filtered.shape}")

    # Save templates for reference
    cv2.imwrite(f"lab/target_{ts}_template.png", tgt_templ)
    cv2.imwrite(f"lab/target_{ts}_template_occ.png", tgt_occ_templ)

    # Template match - standard (as EDAP does it)
    match = cv2.matchTemplate(target_filtered, tgt_templ, cv2.TM_CCOEFF_NORMED)
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)
    print(f"\n  Target match:    score={maxVal:.4f}  loc={maxLoc}  (thresh=0.50)")

    match_occ = cv2.matchTemplate(target_occ_filtered, tgt_occ_templ, cv2.TM_CCOEFF_NORMED)
    (_, maxVal_occ, _, maxLoc_occ) = cv2.minMaxLoc(match_occ)
    print(f"  Occluded match:  score={maxVal_occ:.4f}  loc={maxLoc_occ}  (thresh=0.50)")

    # Draw match location on raw image
    annotated = target_raw.copy()
    tw, th = tgt_templ.shape[::-1]
    if maxVal > 0.3:
        cv2.rectangle(annotated, maxLoc, (maxLoc[0]+tw, maxLoc[1]+th), (0, 255, 0), 2)
        cv2.putText(annotated, f"target={maxVal:.3f}", (maxLoc[0], maxLoc[1]-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    if maxVal_occ > 0.3:
        tw_o, th_o = tgt_occ_templ.shape[::-1]
        cv2.rectangle(annotated, maxLoc_occ, (maxLoc_occ[0]+tw_o, maxLoc_occ[1]+th_o), (0, 165, 255), 2)
        cv2.putText(annotated, f"occ={maxVal_occ:.3f}", (maxLoc_occ[0], maxLoc_occ[1]-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    cv2.imwrite(f"lab/target_{ts}_annotated.png", annotated)
    print(f"  Saved: lab/target_{ts}_annotated.png")

    # Also try multi-scale matching to find optimal scale
    print(f"\n  Multi-scale test (finding best template scale):")
    raw_gray = cv2.cvtColor(target_raw, cv2.COLOR_BGR2GRAY) if len(target_raw.shape) == 3 else target_raw
    orig_templ = cv2.imread("templates/destination.png", cv2.IMREAD_GRAYSCALE)
    if orig_templ is None:
        print("  Could not load templates/destination.png!")
        return

    # Also apply the orange filter to the raw image for matching (same as EDAP does)
    orange_range = [array([16, 165, 220]), array([98, 255, 255])]
    hsv = cv2.cvtColor(target_raw, cv2.COLOR_BGR2HSV)
    filtered_for_match = cv2.inRange(hsv, orange_range[0], orange_range[1])

    best_scale = 0
    best_val = 0
    for scale_pct in range(30, 150, 5):
        s = scale_pct / 100.0
        scaled = cv2.resize(orig_templ, (0, 0), fx=s, fy=s)
        if scaled.shape[0] > filtered_for_match.shape[0] or scaled.shape[1] > filtered_for_match.shape[1]:
            continue
        m = cv2.matchTemplate(filtered_for_match, scaled, cv2.TM_CCOEFF_NORMED)
        (_, mVal, _, mLoc) = cv2.minMaxLoc(m)
        if mVal > best_val:
            best_val = mVal
            best_scale = s
            best_loc = mLoc
        if mVal > 0.4:
            print(f"    scale={s:.2f}: score={mVal:.4f} loc={mLoc}")

    print(f"\n  Best scale: {best_scale:.2f} -> score={best_val:.4f}")
    print(f"  Current EDAP scale: X={scr.scaleX:.3f} Y={scr.scaleY:.3f}")

    if best_val > 0.3:
        # Draw best match
        best_templ = cv2.resize(orig_templ, (0, 0), fx=best_scale, fy=best_scale)
        bw, bh = best_templ.shape[::-1]
        annotated2 = target_raw.copy()
        cv2.rectangle(annotated2, best_loc, (best_loc[0]+bw, best_loc[1]+bh), (255, 0, 255), 2)
        cv2.putText(annotated2, f"best scale={best_scale:.2f} score={best_val:.3f}",
                    (best_loc[0], best_loc[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
        cv2.imwrite(f"lab/target_{ts}_best_scale.png", annotated2)
        print(f"  Saved: lab/target_{ts}_best_scale.png")

    return maxVal


def test_repeated(scr, scr_reg, templ, count=5):
    """Take multiple readings to see consistency."""
    print(f"\n=== Repeated target detection ({count} reads) ===")
    for i in range(count):
        img, (_, maxVal, _, maxLoc), _ = scr_reg.match_template_in_region('target', 'target')
        _, (_, maxVal_occ, _, maxLoc_occ), _ = scr_reg.match_template_in_region('target_occluded', 'target_occluded', inv_col=False)
        found = "FOUND" if maxVal >= 0.50 or maxVal_occ >= 0.50 else "MISS"
        print(f"  [{i+1}] target={maxVal:.4f} loc={maxLoc}  occ={maxVal_occ:.4f} loc={maxLoc_occ}  -> {found}")
        time.sleep(0.5)


def main():
    print("Target Detection Test - Initializing...")
    scr, scr_reg, templ = init_screen()

    while True:
        print("\n--- TARGET TEST MENU ---")
        print("1) Single detection + analysis (saves images)")
        print("2) Repeated detection (5 reads)")
        print("3) Full screenshot + target region overlay")
        print("q) Quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == '1':
            set_focus_elite_window()
            time.sleep(1)
            test_target_detection(scr, scr_reg, templ)
        elif choice == '2':
            set_focus_elite_window()
            time.sleep(1)
            test_repeated(scr, scr_reg, templ)
        elif choice == '3':
            set_focus_elite_window()
            time.sleep(1)
            ts = time.strftime("%H%M%S")
            full = scr.get_screen_full()
            cv2.imwrite(f"lab/target_{ts}_fullscreen.png", full)
            # Draw the target search region on it
            rect = scr_reg.reg['target']['rect']
            h, w = full.shape[:2]
            x1, y1 = int(rect[0]*w), int(rect[1]*h)
            x2, y2 = int(rect[2]*w), int(rect[3]*h)
            annotated = full.copy()
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated, "target search region", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imwrite(f"lab/target_{ts}_fullscreen_region.png", annotated)
            print(f"  Saved: lab/target_{ts}_fullscreen.png")
            print(f"  Saved: lab/target_{ts}_fullscreen_region.png")
            print(f"  Target region: [{rect[0]:.2f}, {rect[1]:.2f}, {rect[2]:.2f}, {rect[3]:.2f}]")
            print(f"  Pixels: ({x1},{y1}) to ({x2},{y2})")
        elif choice == 'q':
            break


if __name__ == "__main__":
    main()
