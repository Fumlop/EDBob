# Image_Templates.py

## Purpose
Manages OpenCV image template loading and scaling for template matching operations. Pre-loads and caches game UI element templates at the correct resolution for screen matching.

## Key Classes/Functions
- Image_Templates: Manages template image loading and scaling

## Key Methods
- load_template(file_name, scale_x, scale_y): Loads PNG as grayscale, resizes to target resolution, returns dict with image and dimensions
- reload_templates(scale_x, scale_y, compass_scale, target_scale): Loads complete template set with different scales for various UI elements

## Template Types
- Navigation: elw, elw_sig, navpoint, navpoint-behind, compass
- Targets: target, target_occluded
- UI: disengage, missions
- Location markers: dest_sirius, robigo_mines, sirius_atmos

## Dependencies
- cv2: OpenCV for image loading and resizing
- os.path: File path operations
- sys: Module path discovery for resource files

## Notes
- Base templates designed for 3440x1440 resolution (ultrawide)
- Separate compass_scale and target_scale parameters for different UI elements
- Grayscale templates optimized for template matching operations
- resource_path() resolves template file paths from current working directory
- Used for image_matchTemplate operations in game automation
