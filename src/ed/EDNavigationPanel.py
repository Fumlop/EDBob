from __future__ import annotations

import os
from copy import copy

import cv2
import numpy as np

from src.core.EDAP_data import GuiFocusExternalPanel
from src.core.EDlogger import logger
from src.screen.Screen_Regions import Quad, Point
from src.ed.StatusParser import StatusParser
from src.ed import MenuNav

"""
File: EDNavigationPanel.py

Description:
  Navigation (left-hand) panel interactions: target row detection for SC Assist,
  docking requests. Menu key sequences are delegated to MenuNav.

  Also exports perspective transform utilities used by EDInternalStatusPanel.

Author: Stumpii
"""


# -- Perspective transform utilities (shared with EDInternalStatusPanel) ------

def image_perspective_transform(image, src_quad: Quad):
    """Deskew a nav/internal panel image via perspective warp.
    Returns (straightened_image, transform, reverse_transform).
    """
    h, w, ch = image.shape
    pts1 = np.float32(src_quad.to_list())
    pts2 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    m = cv2.getPerspectiveTransform(pts1, pts2)
    dst = cv2.warpPerspective(image, m, (w, h))
    rev = cv2.getPerspectiveTransform(pts2, pts1)
    return dst, m, rev


def image_reverse_perspective_transform(image, src_quad: Quad, rev_transform) -> Quad:
    """Reverse-warp coordinates back to skewed panel space for overlay drawing."""
    h, w, ch = image.shape
    q = copy(src_quad)
    q.scale_from_origin(w, h)
    src_arr = np.float32(q.to_list()).reshape(-1, 1, 2)
    dst_arr = cv2.perspectiveTransform(src_arr, rev_transform)
    pts = dst_arr.reshape(-1, dst_arr.shape[-1]).tolist()
    return Quad.from_list(pts)


def rects_to_quadrilateral(rect_tlbr: Quad, rect_bltr: Quad) -> Quad:
    """Convert two bounding rectangles into a quadrilateral (for skewed panels)."""
    return Quad(Point(rect_tlbr.get_left(), rect_tlbr.get_top()),
                Point(rect_bltr.get_right(), rect_bltr.get_top()),
                Point(rect_tlbr.get_right(), rect_tlbr.get_bottom()),
                Point(rect_bltr.get_left(), rect_bltr.get_bottom()))


# -- Navigation Panel class --------------------------------------------------

class EDNavigationPanel:
    """ The Navigation (Left hand) Ship Status Panel. """

    def __init__(self, ed_ap, screen, keys, cb):
        self.screen = screen
        self.keys = keys
        self.ap_ckb = cb
        self.status_parser = StatusParser()

    # -- Target row detection -------------------------------------------------

    # Nav panel list search region (1920x1080 coords)
    NAV_LIST_BOX = (264, 400, 1200, 800)  # x1, y1, x2, y2 (covers all 11 rows)

    # Template matching thresholds
    _bracket_template = None
    _bracket_gt_inv = None
    ORANGE_BRACKET_HIGH = 0.70   # bracket clearly visible (not on target)
    ORANGE_BRACKET_LOW = 0.60    # bracket gone (target selected or not on page)
    INV_BRACKET_THRESHOLD = 0.65 # inverted bracket match = target selected

    @classmethod
    def _load_templates(cls):
        """Load and cache bracket templates."""
        if cls._bracket_template is None:
            tmpl_path = os.path.join(os.path.dirname(__file__), 'templates', 'bracket_lt.png')
            template_lt = cv2.imread(tmpl_path, cv2.IMREAD_GRAYSCALE)
            if template_lt is None:
                logger.error(f"Could not load bracket template from {tmpl_path}")
                return
            cls._bracket_template = template_lt
            template_gt = cv2.flip(template_lt, 1)
            cls._bracket_gt_inv = cv2.bitwise_not(template_gt)

    def _is_target_row_selected(self, seen_bracket: list) -> bool:
        """Check if the currently selected nav panel row is the locked target.

        Combined detection:
        1. Orange mask: template match '<' bracket. High score = bracket visible
           (not on target yet). Score drop + seen_bracket = target found.
        2. Inverted grayscale: match dark '>' on bright row. High score = target
           row is selected (positive confirmation).
        Either method triggering = target found.
        """
        self._load_templates()
        if self._bracket_template is None:
            return False

        img = self.screen.get_screen_full()
        if img is None:
            return False

        x1, y1, x2, y2 = self.NAV_LIST_BOX
        crop = img[y1:y2, x1:x2]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Method 1: orange mask bracket detection (inverted logic)
        orange = cv2.inRange(hsv, np.array([10, 100, 120]), np.array([30, 255, 255]))
        res1 = cv2.matchTemplate(orange, self._bracket_template, cv2.TM_CCOEFF_NORMED)
        _, score_orange, _, _ = cv2.minMaxLoc(res1)

        if score_orange > self.ORANGE_BRACKET_HIGH:
            seen_bracket[0] = True

        orange_hit = seen_bracket[0] and score_orange < self.ORANGE_BRACKET_LOW

        # Method 2: inverted '>' on grayscale (positive detection)
        res2 = cv2.matchTemplate(gray, self._bracket_gt_inv, cv2.TM_CCOEFF_NORMED)
        _, score_inv, _, _ = cv2.minMaxLoc(res2)

        inv_hit = score_inv >= self.INV_BRACKET_THRESHOLD

        is_target = orange_hit or inv_hit
        logger.info(f"nav_target: orange={score_orange:.3f} seen={seen_bracket[0]} inv={score_inv:.3f} -> {'TARGET' if is_target else 'skip'}")

        return is_target

    # -- MenuNav delegates ----------------------------------------------------

    def activate_sc_assist(self) -> bool:
        """Activate Supercruise Assist for the currently locked target."""
        return MenuNav.activate_sc_assist(
            self.keys, self.status_parser,
            is_target_row_fn=self._is_target_row_selected,
            cb=self.ap_ckb
        )

    def request_docking(self) -> bool:
        """Request docking via nav panel."""
        return MenuNav.request_docking(self.keys, self.status_parser)

    def hide_panel(self):
        """Hides the Nav Panel if open."""
        if self.status_parser.get_gui_focus() == GuiFocusExternalPanel:
            MenuNav.goto_cockpit(self.keys, self.status_parser)

    def lock_destination(self, dst_name) -> bool:
        """DEPRECATED: OCR-based nav panel reading removed. Returns False."""
        logger.warning(f"lock_destination('{dst_name}') called but OCR nav panel reading was removed. "
                       f"Use galaxy map favorites instead.")
        return False
