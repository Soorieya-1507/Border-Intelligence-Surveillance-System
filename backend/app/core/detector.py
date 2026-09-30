from ultralytics import YOLO
import cv2
import numpy as np
from app.models.schemas import DetectionSchema

class YOLODetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.model = YOLO(model_path)
        # Class IDs for person, car, motorcycle, bus, truck (COCO)
        self.allowed_classes = [0, 2, 3, 5, 7]
        
    def detect_and_track(self, frame: np.ndarray):
        """
        Runs YOLO tracking on the frame using ByteTrack (default internal tracker).
        Returns a list of DetectionSchema objects with track_ids.
        """
        results = self.model.track(frame, persist=True, classes=self.allowed_classes, verbose=False)
        
        detections = []
        if results and len(results) > 0 and results[0].boxes:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.model.names[cls_id]
                
                track_id = None
                if box.id is not None:
                    track_id = int(box.id[0])
                    
                detections.append(DetectionSchema(
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    class_id=cls_id,
                    class_name=cls_name,
                    track_id=track_id
                ))
        return detections
