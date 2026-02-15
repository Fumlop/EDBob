# MachineLearning.py

## Purpose
Machine learning inference wrapper using YOLOv8 for object detection in Elite Dangerous. Detects and localizes game UI elements like compass, targets, and navigation markers.

## Key Classes/Functions
- MachLeanMatch: Dataclass representing a detection result
- MachLearn: Inference engine wrapper for YOLOv8 model

## Key Methods
- __init__(ed_ap, cb): Loads pre-trained YOLOv8 model from runs/detect/train7/weights/best.pt
- predict(image): Runs inference on image, returns list of MachLeanMatch detections or None

## MachLeanMatch Fields
- class_name: Detected class (e.g., 'compass', 'target')
- match_pct: Confidence score (0.0-1.0)
- bounding_quad: Bounding box as Quad region

## Detection Output
- Returns list of MachLeanMatch objects, one per detection
- Each detection includes class name, confidence, and bounding box coordinates
- Returns None if no detections found

## Dependencies
- ultralytics.YOLO: YOLOv8 model implementation
- cv2: Image handling (passed to predict)
- Screen_Regions.Quad: Bounding box representation

## Notes
- Model trained on Elite Dangerous UI elements (train7 iteration)
- Requires pre-trained weights at runs/detect/train7/weights/best.pt
- Verbose output disabled during inference (verbose=False)
- Bounding boxes converted from model format (xyxy) to Quad format
- Used for robust compass and target detection vs template matching
