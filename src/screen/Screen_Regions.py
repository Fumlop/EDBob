import json
import logging
import os
from copy import copy

import numpy as np
from numpy import array, sum
import cv2

logger = logging.getLogger('Screen_Regions')
"""
File:Screen_Regions.py    

Description:
  Class to rectangle areas of the screen to capture along with filters to apply. Includes functions to
  match a image template to the region using opencv 

"""


class Screen_Regions:
    # Map region names to their filter callback and color range
    _REGION_FILTERS = {
        'compass':       ('equalize',       None),
        'target':        ('filter_by_color', 'orange_2_color_range'),
        'sun':           ('filter_sun',      None),
        'disengage':     ('filter_by_color', 'blue_sco_color_range'),
        'sco':           ('filter_by_color', 'blue_sco_color_range'),
        'sc_assist_ind': ('filter_by_color', 'cyan_sc_assist_range'),
        'mission_dest':  ('equalize',        None),
        'missions':      ('equalize',        None),
        'nav_panel':     ('equalize',        None),
        'center_text':   ('filter_by_color', 'orange_color_range'),
    }

    def __init__(self, screen, ship_type=None):
        self.screen = screen
        self.regions_loaded = False

        self.sun_threshold = 125

        # HSV color ranges for filtering
        self.orange_color_range   = [array([0, 130, 123]),  array([25, 235, 220])]
        self.orange_2_color_range = [array([16, 165, 220]), array([98, 255, 255])]
        self.blue_color_range     = [array([0, 28, 170]), array([180, 100, 255])]
        self.blue_sco_color_range = [array([10, 0, 0]), array([100, 150, 255])]
        self.cyan_sc_assist_range = [array([80, 80, 80]), array([110, 255, 255])]

        self.reg = {}
        self._load_regions(ship_type)

    def _load_regions(self, ship_type=None):
        """Load screen regions from JSON config file.
        Tries ship-specific config first, falls back to default.json.
        """
        w = self.screen.screen_width
        h = self.screen.screen_height
        base_dir = f'configs/screen_regions/res_{w}_{h}'

        config_data = None
        # Try ship-specific config, then default
        candidates = []
        if ship_type:
            candidates.append(os.path.join(base_dir, f'{ship_type}.json'))
        candidates.append(os.path.join(base_dir, 'default.json'))

        for path in candidates:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    config_data = json.load(f)
                logger.info(f"Loaded screen regions from {path}")
                break

        # Build reg dict from config + filter definitions
        self.reg = {}
        for name, region_info in config_data['regions'].items():
            rect = region_info['rect']
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            filter_cb = None
            filter_range = None
            if name in self._REGION_FILTERS:
                cb_name, range_name = self._REGION_FILTERS[name]
                filter_cb = getattr(self, cb_name)
                if range_name:
                    filter_range = getattr(self, range_name)

            self.reg[name] = {
                'rect': rect,
                'width': width,
                'height': height,
                'filterCB': filter_cb,
                'filter': filter_range,
            }

        self.regions_loaded = True

    def reload_regions(self, ship_type=None):
        """Reload regions, e.g. when ship changes."""
        self._load_regions(ship_type)

    def capture_region(self, screen, region_name):
        """Grab screen region by name. Returns BGRA (raw from mss)."""
        return screen.get_screen_region(self.reg[region_name]['rect'])

    def capture_region_filtered(self, screen, region_name):
        """Grab screen region and apply its filter. Returns filtered image."""
        scr = screen.get_screen_region(self.reg[region_name]['rect'])
        if self.reg[region_name]['filterCB'] is None:
            # return the screen region untouched in BGRA format.
            return scr
        else:
            # return the screen region in the format returned by the filter.
            return self.reg[region_name]['filterCB'](scr, self.reg[region_name]['filter'])

    def equalize(self, image=None, noOp=None):
        # Load the image in greyscale
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # create a CLAHE object (Arguments are optional).  Histogram equalization, improves constrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_out = clahe.apply(img_gray)

        return img_out

    def filter_by_color(self, image, color_range):
        """Filters an image based on a given color range.
        Returns the filtered image. Pixels within the color range are returned
        their original color, otherwise black."""
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # filter passed in color low, high
        filtered = cv2.inRange(hsv, color_range[0], color_range[1])

        return filtered

    # not used
    def filter_bright(self, image=None, noOp=None):
        equalized = self.equalize(image)
        equalized = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)  #hhhmm, equalize() already converts to gray
        equalized = cv2.cvtColor(equalized, cv2.COLOR_BGR2HSV)
        filtered = cv2.inRange(equalized, array([0, 0, 215]), array([0, 0, 255]))  #only high value

        return filtered

    def set_sun_threshold(self, thresh):
        self.sun_threshold = thresh

    # need to compare filter_sun with filter_bright
    def filter_sun(self, image=None, noOp=None):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # set low end of filter to 25 to pick up the dull red Class L stars
        (thresh, blackAndWhiteImage) = cv2.threshold(hsv, self.sun_threshold, 255, cv2.THRESH_BINARY)

        return blackAndWhiteImage

    # percent the image is white
    def sun_percent(self, screen):
        blackAndWhiteImage = self.capture_region_filtered(screen, 'sun')

        wht = sum(blackAndWhiteImage == 255)
        blk = sum(blackAndWhiteImage != 255)

        result = int((wht / (wht + blk)) * 100)

        return result


class Point:
    """Creates a point on a coordinate plane with values x and y."""

    def __init__(self, x, y):
        """Defines x and y variables"""
        self.x: float = x
        self.y: float = y

    def __str__(self):
        return "Point(%s, %s)" % (self.x, self.y)

    def get_x(self) -> float:
        return self.x

    def get_y(self) -> float:
        return self.y

    def to_list(self) -> [float, float]:
        return [self.x, self.y]

    @classmethod
    def from_xy(cls, xy_tuple: (float, float)):
        """ From (x, y) """
        return cls(xy_tuple[0], xy_tuple[1])

    @classmethod
    def from_list(cls, xy_list: [float, float]):
        """ From (x, y) """
        return cls(xy_list[0], xy_list[1])


class Quad:
    """ Represents a quadrilateral (a four-sided polygon that has four edges and four vertices).
    It can be classified into various types, such as squares, rectangles, trapezoids, and rhombuses.
    """

    def __init__(self, p1: Point = None, p2: Point = None, p3: Point = None, p4: Point = None):
        self.pt1: Point = p1
        self.pt2: Point = p2
        self.pt3: Point = p3
        self.pt4: Point = p4

    @classmethod
    def from_list(cls, pt_list: [[float, float], [float, float], [float, float], [float, float]]):
        """ Creates a quad from a list of points as
        [[left, top], [right, top], [right, bottom], [left, bottom]]."""
        return cls(Point.from_list(pt_list[0]), Point.from_list(pt_list[1]),
                   Point.from_list(pt_list[2]), Point.from_list(pt_list[3]))

    @classmethod
    def from_rect(cls, pt_list: [float, float, float, float]):
        """ Creates a quad from a list of points as [left, top, right, bottom] """
        return cls(Point(pt_list[0], pt_list[1]), Point(pt_list[2], pt_list[1]),
                   Point(pt_list[2], pt_list[3]), Point(pt_list[0], pt_list[3]))

    def to_rect_list(self, round_dp: int = -1) -> [float, float, float, float]:
        """ Returns the bounds of the quadrilateral as a list of values [left, top, right, bottom].
        @param: round_dp: If >=0, the number of decimal places to round numbers to, otherwise no rounding.
        """
        if round_dp < 0:
            return [self.get_left(), self.get_top(), self.get_right(), self.get_bottom()]
        else:
            return [round(self.get_left(), round_dp), round(self.get_top(), round_dp),
                    round(self.get_right(), round_dp), round(self.get_bottom(), round_dp)]

    def to_list(self) -> [[float, float], [float, float], [float, float], [float, float]]:
        """ Returns the list of points of the quadrilateral as
        [[left, top], [right, top], [right, bottom], [left, bottom]]."""
        return [self.pt1.to_list(), self.pt2.to_list(), self.pt3.to_list(), self.pt4.to_list()]

    def get_top_left(self) -> Point:
        """ Returns the top left point. """
        pt = self.pt1
        if self.pt2.x < pt.x and self.pt2.y < pt.y:
            pt = self.pt2
        if self.pt3.x < pt.x and self.pt3.y < pt.y:
            pt = self.pt3
        if self.pt4.x < pt.x and self.pt4.y < pt.y:
            pt = self.pt4
        return copy(pt)

    def get_bottom_right(self) -> Point:
        """ Returns the bottom right point. """
        pt = self.pt1
        if self.pt2.x > pt.x and self.pt2.y > pt.y:
            pt = self.pt2
        if self.pt3.x > pt.x and self.pt3.y > pt.y:
            pt = self.pt3
        if self.pt4.x > pt.x and self.pt4.y > pt.y:
            pt = self.pt4
        return copy(pt)

    def get_left(self) -> float:
        """ Returns the value of the left most point. """
        return min(self.pt1.x, self.pt2.x, self.pt3.x, self.pt4.x)

    def get_top(self) -> float:
        """ Returns the value of the top most point. """
        return min(self.pt1.y, self.pt2.y, self.pt3.y, self.pt4.y)

    def get_right(self) -> float:
        """ Returns the value of the right most point. """
        return max(self.pt1.x, self.pt2.x, self.pt3.x, self.pt4.x)

    def get_bottom(self) -> float:
        """ Returns the value of the bottom most point. """
        return max(self.pt1.y, self.pt2.y, self.pt3.y, self.pt4.y)

    def get_width(self):
        """Returns the maximum width."""
        return self.get_right() - self.get_left()

    def get_height(self):
        """Returns the maximum height."""
        return self.get_bottom() - self.get_top()

    def get_bounds(self) -> (Point, Point):
        """ Returns the bounds of the quadrilateral as a rectangle defined by two points,
        the top-left and bottom-right."""
        return Point(self.get_left(), self.get_top()), Point(self.get_right(), self.get_bottom())

    def get_center(self) -> Point:
        cx = (self.pt1.x + self.pt2.x + self.pt3.x + self.pt4.x) / 4
        cy = (self.pt1.y + self.pt2.y + self.pt3.y + self.pt4.y) / 4
        return Point(cx, cy)

    def scale(self, fx: float, fy: float):
        """ Scales the quad from the center.
        @param fy: Scaling in the Y direction.
        @param fx: Scaling in the X direction.
        """
        center = self.get_center()
        self.pt1 = self._scale_point(self.pt1, center, fx, fy)
        self.pt2 = self._scale_point(self.pt2, center, fx, fy)
        self.pt3 = self._scale_point(self.pt3, center, fx, fy)
        self.pt4 = self._scale_point(self.pt4, center, fx, fy)

    def inflate(self, x: float, y: float):
        """ Scales the quad from the center.
        @param fy: Scaling in the Y direction.
        @param fx: Scaling in the X direction.
        """
        center = self.get_center()
        self.pt1 = self._inflate_point(self.pt1, center, x, y)
        self.pt2 = self._inflate_point(self.pt2, center, x, y)
        self.pt3 = self._inflate_point(self.pt3, center, x, y)
        self.pt4 = self._inflate_point(self.pt4, center, x, y)

    def subregion_from_quad(self, quad):
        """ Crops the quad as region specified by the % (0.0-1.0) inputs.
        NOTE: This assumes that the quad is a rectangle or square. Won't work with other shapes!
        Example: An input of [0.0, 0.0, 1.0, 1.0] returns the quad unchanged.
        Example: An input of [0.0, 0.0, 0.25, 0.25] returns the top left quarter of the quad.
        @param quad: A quad.
        """
        new_l = (quad.get_left() * self.get_width()) + self.get_left()
        new_t = (quad.get_top() * self.get_height()) + self.get_top()
        new_r = (quad.get_right() * self.get_width()) + self.get_left()
        new_b = (quad.get_bottom() * self.get_height()) + self.get_top()

        self.pt1 = Point(new_l, new_t)
        self.pt2 = Point(new_r, new_t)
        self.pt3 = Point(new_r, new_b)
        self.pt4 = Point(new_l, new_b)

    def scale_from_origin(self, fx: float, fy: float):
        """ Scales the quad from the origin (0,0).
        @param fy: Scaling in the Y direction.
        @param fx: Scaling in the X direction.
        """
        origin = Point(0, 0)
        self.pt1 = self._scale_point(self.pt1, origin, fx, fy)
        self.pt2 = self._scale_point(self.pt2, origin, fx, fy)
        self.pt3 = self._scale_point(self.pt3, origin, fx, fy)
        self.pt4 = self._scale_point(self.pt4, origin, fx, fy)

    def offset(self, dx: float, dy: float):
        """ Offsets (moves) the quad by the given amount.
        @param dx: The amount to move in the x direction.
        @param dy: The amount to move in the y direction.
        """
        self.pt1 = self._offset_point(self.pt1, dx, dy)
        self.pt2 = self._offset_point(self.pt2, dx, dy)
        self.pt3 = self._offset_point(self.pt3, dx, dy)
        self.pt4 = self._offset_point(self.pt4, dx, dy)

    @staticmethod
    def _scale_point(pt: Point, center: Point, fx: float, fy: float) -> Point:
        return Point(
            center.x + (pt.x - center.x) * fx,
            center.y + (pt.y - center.y) * fy
        )

    @staticmethod
    def _inflate_point(pt: Point, center: Point, x: float, y: float) -> Point:
        x1 = x
        y1 = y
        if pt.x < center.x:
            x1 = -x
        if pt.y < center.y:
            y1 = -y
        return Point(pt.x + x1, pt.y + y1)

    @staticmethod
    def _offset_point(pt: Point, dx: float, dy: float) -> Point:
        """ Offsets the point.
        Using this instead of calling offset on the point directly allows shallow copy of the quad."""
        return Point(pt.x + dx, pt.y + dy)

    def __str__(self):
        return (f"Quadrilateral:\n"
                f" pt1: ({self.pt1.x}, {self.pt1.y})\n"
                f" pt2: ({self.pt2.x}, {self.pt2.y})\n"
                f" pt3: ({self.pt3.x}, {self.pt3.y})\n"
                f" pt4: ({self.pt4.x}, {self.pt4.y})")
