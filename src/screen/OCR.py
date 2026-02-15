from __future__ import annotations
import time

import cv2
import numpy as np
from cv2.typing import MatLike
from strsimpy.normalized_levenshtein import NormalizedLevenshtein
from src.core.EDlogger import logger

from src.screen.Screen_Regions import Quad

"""
File:OCR.py

Description:
  Class for screen element detection using OpenCV color/shape analysis.
  PaddleOCR has been removed -- UI checks use pixel color detection instead.

Author: Stumpii
"""


class OCR:
    def __init__(self, ed_ap, screen):
        self.ap = ed_ap
        self.screen = screen
        self.normalized_levenshtein = NormalizedLevenshtein()

    def string_similarity(self, s1: str, s2: str) -> float:
        """ Performs a string similarity check and returns the result.
        @param s1: The first string to compare.
        @param s2: The second string to compare.
        @return: The similarity from 0.0 (no match) to 1.0 (identical).
        """
        s1_new = s1.replace("['",  "")
        s1_new = s1_new.replace("']",  "")
        s1_new = s1_new.replace('["',  "")
        s1_new = s1_new.replace('"]',  "")
        s1_new = s1_new.replace("', '",  "")
        s1_new = s1_new.replace("<",  "")
        s1_new = s1_new.replace(">",  "")
        s1_new = s1_new.replace("-",  "")
        s1_new = s1_new.replace("—",  "")
        s1_new = s1_new.replace(" ",  "")

        s2_new = s2.replace("['",  "")
        s2_new = s2_new.replace("']",  "")
        s2_new = s2_new.replace('["',  "")
        s2_new = s2_new.replace('"]',  "")
        s2_new = s2_new.replace("', '",  "")
        s2_new = s2_new.replace("<",  "")
        s2_new = s2_new.replace(">",  "")
        s2_new = s2_new.replace("-",  "")
        s2_new = s2_new.replace("—",  "")
        s2_new = s2_new.replace(" ",  "")

        return self.normalized_levenshtein.similarity(s1_new, s2_new)

    @staticmethod
    def get_highlighted_item_in_image(image, item: Quad) -> (MatLike, Quad):
        """ Attempts to find a selected item in an image. The selected item is identified by being solid orange or blue
        rectangle with dark text, instead of orange/blue text on a dark background.
        The image of the first item matching the criteria and minimum width and height is returned
        with x and y co-ordinates, otherwise None.
        @param item: A Quad representing the item in percent.
        @param image: The image to check.
        @return: The highlighted image and the matching Quad position in percentage of the image size, or (None, None)
        """
        min_w = item.get_width()
        min_h = item.get_height()

        # Existing size
        img_h, img_w, _ = image.shape

        # The input image
        cv2.imwrite('test/nav-panel/out/1-input.png', image)

        # Perform HSV mask
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_range = np.array([0, 100, 180])
        upper_range = np.array([255, 255, 255])
        mask = cv2.inRange(hsv, lower_range, upper_range)
        masked_image = cv2.bitwise_and(image, image, mask=mask)
        cv2.imwrite('test/nav-panel/out/2-masked.png', masked_image)

        # Convert to gray scale and invert
        gray = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
        cv2.imwrite('test/nav-panel/out/3-gray.png', gray)

        # Convert to B&W to allow FindContours to find rectangles.
        ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
        cv2.imwrite('test/nav-panel/out/4-thresh1.png', thresh1)

        # Perform opening. Opening is just another name of erosion followed by dilation. This will remove specs and
        # edges and then embolden the remaining edges. This works to remove text and stray lines.
        k = int(min(img_w * min_w, img_h * min_h) / 10)  # Make kernel 10% of the smallest image side
        kernel = np.ones((k, k), np.uint8)
        opening = cv2.morphologyEx(thresh1, cv2.MORPH_OPEN, kernel)
        cv2.imwrite('test/nav-panel/out/5-opened.png', opening)

        # Finding contours in B&W image. White are the areas detected
        contours, hierarchy = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        output = image
        cv2.drawContours(output, contours, -1, (0, 255, 0), 2)
        cv2.imwrite('test/nav-panel/out/6-contours.png', output)

        cropped = image
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Check the item is greater than 85% of the minimum width or height.
            if w > (img_w * min_w * 0.85) and h > (img_h * min_h * 0.85):
                # Crop to leave only the contour (the selected rectangle)
                cropped = image[y:y + h, x:x + w]

                cv2.imwrite('test/nav-panel/out/7-selected_item.png', cropped)
                q = Quad.from_rect([x / img_w, y / img_h, (x + w) / img_w, (y + h) / img_h])
                return cropped, q

        # No good matches, then return None
        return None, None

    def capture_region_pct(self, region):
        """ Grab the image based on the region name/rect.
        Returns an unfiltered image, either from screenshot or provided image.
        @param region: The region to check in % (0.0 - 1.0).
        """
        rect = region['rect']
        image = self.screen.get_screen_rect_pct(rect)
        return image

    def wait_for_ui_element(self, ap, region, timeout=15, color='orange') -> bool:
        """ Wait for a UI element to appear by checking for colored pixels in a region.
        Replaces wait_for_text -- instead of OCR, counts orange/white pixels via HSV filtering.
        @param ap: ED_AP instance.
        @param region: The screen region to check in % (0.0 - 1.0) of the full screen.
        @param timeout: Time to wait for element in seconds.
        @param color: Color to detect -- 'orange' for ED UI text, 'white' for white text.
        @return: True if enough colored pixels found, else False.
        """
        # Draw box around region
        abs_rect = self.screen.screen_rect_to_abs(region['rect'])
        if ap.debug_overlay:
            ap.overlay.overlay_rect1('wait_for_ui_element', abs_rect, (0, 255, 0), 2)
            ap.overlay.overlay_paint()

        # HSV ranges for ED UI colors
        if color == 'orange':
            lower = np.array([10, 100, 150])
            upper = np.array([30, 255, 255])
        else:  # white
            lower = np.array([0, 0, 200])
            upper = np.array([180, 40, 255])

        # Minimum pixel count threshold (relative to region size)
        min_pixel_ratio = 0.01  # 1% of region must be the target color

        start_time = time.time()
        while True:
            if time.time() > (start_time + timeout):
                return False

            image = self.capture_region_pct(region)
            if image is None:
                time.sleep(0.25)
                continue

            # Convert to HSV and count matching pixels
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower, upper)
            pixel_count = cv2.countNonZero(mask)
            total_pixels = image.shape[0] * image.shape[1]
            ratio = pixel_count / total_pixels if total_pixels > 0 else 0

            if ap.debug_overlay:
                ap.overlay.overlay_floating_text('wait_for_ui_element',
                                                 f'pixels: {pixel_count} ({ratio:.3f})',
                                                 abs_rect[0], abs_rect[1] - 25, (0, 255, 0))
                ap.overlay.overlay_paint()

            if ratio >= min_pixel_ratio:
                return True

            time.sleep(0.25)

        return False

    def detect_highlighted_tab_index(self, tab_bar_image, num_tabs) -> int:
        """ Detect which tab is highlighted (active) in a tab bar image by finding
        the orange highlight rectangle position.
        @param tab_bar_image: Image of the tab bar.
        @param num_tabs: Number of tabs expected.
        @return: 0-based tab index, or -1 if not found.
        """
        if tab_bar_image is None:
            return -1

        img_h, img_w = tab_bar_image.shape[:2]

        # HSV filter for orange highlight (solid orange tab background)
        hsv = cv2.cvtColor(tab_bar_image, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 100, 180])
        upper = np.array([255, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

        # Find the x-center of the highlighted region
        coords = cv2.findNonZero(mask)
        if coords is None:
            return -1

        # Get average x position of highlighted pixels
        avg_x = np.mean(coords[:, 0, 0])

        # Map x position to tab index
        tab_width = img_w / num_tabs
        tab_index = int(avg_x / tab_width)
        return min(tab_index, num_tabs - 1)
