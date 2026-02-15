# Screen_Regions.py

## Purpose
Defines screen regions for Elite Dangerous interface capture, provides template matching functionality with various image filters, and includes geometric classes for handling rectangle and quadrilateral shapes.

## Key Classes/Functions
- **Screen_Regions**: Manages screen regions with filters and provides template matching
- **Point**: Represents a coordinate point with x, y values
- **Quad**: Represents a quadrilateral shape with transformation and manipulation methods
- **load_ocr_calibration_data()**: Loads OCR calibration regions from JSON configuration
- **load_calibrated_regions()**: Applies calibrated region sizes to region dictionary
- **scale_region()**: Converts sub-region percentages to parent region coordinates

## Key Methods

### Screen_Regions Class

- **__init__(screen, templ)**: Initializes regions, color ranges, and matching thresholds for compass, target, sun, FSS, missions, and navigation panel
- **capture_region(screen, region_name, inv_col)**: Captures unfiltered screenshot of named region
- **capture_region_filtered(screen, region_name, inv_col)**: Captures screenshot and applies region's filter function
- **match_template_in_region(region_name, templ_name, inv_col)**: Matches template in filtered region, returns image and match details
- **match_template_in_region_x3(region_name, templ_name, inv_col)**: Matches template against HSV channel splits, returns best match
- **match_template_in_image(image, template)**: Matches template in arbitrary image
- **match_template_in_image_x3(image, templ_name)**: Matches template against HSV splits in arbitrary image
- **equalize(image, noOp)**: Applies CLAHE histogram equalization to improve contrast
- **filter_by_color(image, color_range)**: Filters image by HSV color range
- **filter_sun(image, noOp)**: Applies threshold filter for detecting stars/suns
- **set_sun_threshold(thresh)**: Sets threshold value for sun detection
- **sun_percent(screen)**: Returns percentage of white pixels in sun region

### Point Class

- **__init__(x, y)**: Creates point with x, y coordinates
- **get_x()**: Returns x coordinate
- **get_y()**: Returns y coordinate
- **to_list()**: Returns point as [x, y] list
- **from_xy(xy_tuple)**: Class method to create from (x, y) tuple
- **from_list(xy_list)**: Class method to create from [x, y] list

### Quad Class

- **__init__(p1, p2, p3, p4)**: Creates quad from four Point objects
- **from_list(pt_list)**: Class method to create from [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
- **from_rect(pt_list)**: Class method to create from [left, top, right, bottom] rectangle
- **to_rect_list(round_dp)**: Returns quad bounds as [left, top, right, bottom]
- **to_list()**: Returns quad points as list of [x, y] coordinates
- **get_left()**: Returns leftmost x coordinate
- **get_top()**: Returns topmost y coordinate
- **get_right()**: Returns rightmost x coordinate
- **get_bottom()**: Returns bottommost y coordinate
- **get_width()**: Returns maximum width
- **get_height()**: Returns maximum height
- **get_top_left()**: Returns top-left corner as Point
- **get_bottom_right()**: Returns bottom-right corner as Point
- **get_bounds()**: Returns bounding rectangle as tuple of (top-left Point, bottom-right Point)
- **get_center()**: Returns center point of quad
- **scale(fx, fy)**: Scales quad from center point
- **inflate(x, y)**: Expands quad from center by pixel amounts
- **subregion_from_quad(quad)**: Crops quad to percentage-based region (0.0-1.0)
- **scale_from_origin(fx, fy)**: Scales quad from origin (0,0)
- **offset(dx, dy)**: Moves quad by given pixel amounts

## Dependencies
- opencv-python (cv2)
- numpy
- json
- os
- datetime
- typing (TypedDict)
- copy

## Notes
- Predefined regions target key ED interface elements: compass, target, sun, disengage button, FSS, missions, navigation panel
- Regions are stored as percentage coordinates [L, T, R, B] (0.0 to 1.0) then converted to pixel coordinates during initialization
- Color ranges defined in HSV color space for robust color-based filtering
- Template matching uses TM_CCOEFF_NORMED correlation coefficient method
- HSV channel splitting (x3 methods) provides robust matching by testing each channel separately and selecting best result
- Calibration data can be loaded from configs/ocr_calibration.json to customize region boundaries
- Quad class assumes rectangular geometry for subregion operations (not applicable to non-rectangular quads)
