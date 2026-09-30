import cv2
import threading
import time
from typing import Callable
from app.core.detector import YOLODetector
from app.core.analytics.virtual_fence import VirtualFence
from app.core.analytics.loitering import LoiteringEngine
from app.core.analytics.risk_engine import RiskEngine
from app.config import settings
import uuid

class StreamManager:
    def __init__(self, camera_id: str, source_url: str):
        self.camera_id = camera_id
        self.source_url = source_url
        self.cap = None
        self.is_running = False
        self.thread = None
        
        # Modules
        self.detector = YOLODetector()
        self.fences = {zone.name: VirtualFence(zone) for zone in settings.DEFAULT_ZONES}
        self.loitering_engines = {zone.name: LoiteringEngine() for zone in settings.DEFAULT_ZONES}
        
        # State
        self.tracks_history = {} # track_id -> list of centroids
        self.last_time = time.time()
        
        # Callbacks
        self.on_frame_callback = None
        self.on_event_callback = None
        
    def start(self):
        if self.is_running:
            return
        self.cap = cv2.VideoCapture(self.source_url)
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            
    def _process_loop(self):
        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                # Re-loop video for testing purposes
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            # 1. Detection & Tracking
            detections = self.detector.detect_and_track(frame)
            
            rendered_frame = frame.copy()
            alerts = []
            
            # 2. Analytics per track
            for det in detections:
                if det.track_id is None:
                    continue
                    
                x1, y1, x2, y2 = det.bbox
                centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
                
                # Maintain history for trajectory
                if det.track_id not in self.tracks_history:
                    self.tracks_history[det.track_id] = []
                hist = self.tracks_history[det.track_id]
                hist.append(centroid)
                if len(hist) > 30: # Keep last 30 frames
                    hist.pop(0)
                    
                prev_centroid = hist[-2] if len(hist) >= 2 else centroid
                
                # Check Zones
                for zone_name, fence in self.fences.items():
                    # Virtual Fence Check
                    crossing = fence.check_crossing(prev_centroid, centroid)
                    is_inside = fence.is_inside(centroid)
                    
                    # Loitering Check
                    dwell_time = self.loitering_engines[zone_name].update(det.track_id, is_inside, dt)
                    
                    factors = []
                    rule_triggered = None
                    
                    if crossing["crossed"]:
                        if not crossing["allowed"]:
                            factors.append("Wrong Direction")
                        else:
                            factors.append("Base Intrusion")
                        rule_triggered = f"Fence Crossed ({crossing['type']})"
                        
                    elif dwell_time > fence.zone.loitering_threshold_sec:
                        # Ensure we don't alert every single frame after threshold
                        # In MVP, we might trigger continuously, but we should debounce in production
                        # For now, let's trigger an event every 5 seconds of loitering
                        if int(dwell_time) % 5 == 0 and dwell_time - int(dwell_time) < dt*1.5:
                            factors.append("Loitering Exceeded")
                            rule_triggered = f"Loitering > {fence.zone.loitering_threshold_sec}s"

                    if factors:
                        score, risk_factors = RiskEngine.calculate_risk(factors)
                        incident = {
                            "incident_id": str(uuid.uuid4()),
                            "camera_id": self.camera_id,
                            "timestamp": current_time,
                            "entity_type": det.class_name,
                            "track_id": det.track_id,
                            "rule_triggered": f"{zone_name}: {rule_triggered}",
                            "risk_score": score,
                            "risk_factors": [rf.model_dump() for rf in risk_factors]
                        }
                        alerts.append(incident)
                        if self.on_event_callback:
                            self.on_event_callback(incident)
                            
                # Draw boxes and tracks
                color = (0, 255, 0) if not alerts else (0, 0, 255)
                cv2.rectangle(rendered_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(rendered_frame, f"{det.class_name}-{det.track_id}", (int(x1), int(y1)-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw Fences
            for zone_name, fence in self.fences.items():
                pts = fence.polygon_pts
                cv2.polylines(rendered_frame, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
                
            if self.on_frame_callback:
                self.on_frame_callback(self.camera_id, rendered_frame, detections, alerts)
                
            # Simulate real-time if processing is faster than FPS
            time.sleep(max(0.01, 0.033 - dt))
