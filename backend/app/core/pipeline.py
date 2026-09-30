import cv2
import time
import uuid
import os
import numpy as np
from typing import Dict, Any, List, Tuple
from app.core.detector import YOLODetector
from app.core.analytics.virtual_fence import VirtualFence
from app.core.analytics.loitering import LoiteringEngine
from app.core.analytics.risk_engine import RiskEngine
from app.config import settings
from app.api.ws_telemetry import broadcast_frame

class AnalyticsPipeline:
    """
    Production-grade AI analytics orchestrator tailored for MHA/SSB surveillance.
    Processes multi-camera feeds with decoupled zones, loitering debouncing,
    snapshot generation, and explainable risk scores.
    """
    def __init__(self):
        self.detector = YOLODetector()
        
        # Initialize camera-specific virtual fences & loitering engines
        self.camera_fences: Dict[str, Dict[str, VirtualFence]] = {}
        self.camera_loitering: Dict[str, Dict[str, LoiteringEngine]] = {}
        
        for cam_id, cam_cfg in settings.CAMERAS.items():
            self.camera_fences[cam_id] = {
                zone.name: VirtualFence(zone) for zone in cam_cfg["zones"]
            }
            self.camera_loitering[cam_id] = {
                zone.name: LoiteringEngine() for zone in cam_cfg["zones"]
            }
            
        # Per-camera track history: (cam_id, track_id) -> list of centroids
        self.tracks_history: Dict[Tuple[str, int], List[Tuple[float, float]]] = {}
        self.last_process_time: Dict[str, float] = {}
        
        # Ensure snapshot directory exists
        self.snapshot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/snapshots"))
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def process_frame(self, camera_id: str, frame: np.ndarray, timestamp: float, stream_telemetry: Dict[str, Any]):
        current_time = time.time()
        prev_time = self.last_process_time.get(camera_id, current_time)
        dt = max(current_time - prev_time, 0.001)
        self.last_process_time[camera_id] = current_time

        # 1. Multi-Object Detection & Tracking
        detections = self.detector.detect_and_track(frame)
        rendered_frame = frame.copy()
        alerts = []
        
        fences = self.camera_fences.get(camera_id, {})
        loitering_engines = self.camera_loitering.get(camera_id, {})

        # 2. Track Trajectory & Zone Policy Evaluation
        for det in detections:
            if det.track_id is None:
                continue

            x1, y1, x2, y2 = det.bbox
            centroid = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            track_key = (camera_id, det.track_id)

            if track_key not in self.tracks_history:
                self.tracks_history[track_key] = []
            hist = self.tracks_history[track_key]
            hist.append(centroid)
            if len(hist) > 30:
                hist.pop(0)

            prev_centroid = hist[-2] if len(hist) >= 2 else centroid

            # Check Zone Policies
            for zone_name, fence in fences.items():
                crossing = fence.check_crossing(prev_centroid, centroid)
                is_inside = fence.is_inside(centroid)
                dwell_time = loitering_engines[zone_name].update(det.track_id, is_inside, dt)

                factors = []
                rule_triggered = None

                if crossing["crossed"]:
                    if not crossing["allowed"]:
                        factors.append("Wrong Direction")
                    else:
                        factors.append("Base Intrusion")
                    rule_triggered = f"Perimeter Breach ({crossing['type']})"
                elif dwell_time > fence.zone.loitering_threshold_sec:
                    # Debounce loitering alerts to trigger every 4 seconds
                    if int(dwell_time) % 4 == 0 and (dwell_time - int(dwell_time)) < dt * 1.5:
                        factors.append("Loitering Exceeded")
                        rule_triggered = f"Suspicious Loiter ({int(dwell_time)}s in zone)"

                if factors:
                    score, risk_factors = RiskEngine.calculate_risk(factors)
                    incident_id = str(uuid.uuid4())[:8].upper()
                    
                    # Save keyframe snapshot for evidence replay
                    snapshot_filename = f"incident_{incident_id}.jpg"
                    snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)
                    cv2.imwrite(snapshot_path, frame)

                    incident = {
                        "incident_id": f"IBVAP-{incident_id}",
                        "camera_id": camera_id,
                        "location": settings.CAMERAS.get(camera_id, {}).get("location", "Border Sector"),
                        "timestamp": current_time,
                        "entity_type": det.class_name.upper(),
                        "track_id": det.track_id,
                        "rule_triggered": f"{zone_name}: {rule_triggered}",
                        "risk_score": score,
                        "risk_factors": [rf.model_dump() for rf in risk_factors],
                        "snapshot_url": f"/snapshots/{snapshot_filename}"
                    }
                    alerts.append(incident)

            # Draw tactical overlay: entity box, track ID, confidence
            box_color = (0, 0, 255) if alerts else (0, 255, 0)
            cv2.rectangle(rendered_frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)
            label = f"{det.class_name.upper()} #{det.track_id} ({int(det.confidence*100)}%)"
            
            # Label background pill
            t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
            cv2.rectangle(rendered_frame, (int(x1), int(y1) - 18), (int(x1) + t_size[0] + 6, int(y1)), (0, 0, 0), -1)
            cv2.putText(rendered_frame, label, (int(x1) + 3, int(y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            # Draw trajectory path
            if len(hist) > 1:
                pts = np.array(hist, np.int32).reshape((-1, 1, 2))
                cv2.polylines(rendered_frame, [pts], isClosed=False, color=(255, 200, 0), thickness=2)

        # Draw Zone Polygons
        for zone_name, fence in fences.items():
            pts = fence.polygon_pts
            zone_color = (0, 60, 255) if "Red" in zone_name or "Restricted" in zone_name else (0, 215, 255)
            cv2.polylines(rendered_frame, [pts], isClosed=True, color=zone_color, thickness=2)
            
            # Zone label
            if len(pts) > 0:
                first_pt = pts[0][0]
                cv2.putText(rendered_frame, zone_name.upper(), (int(first_pt[0]) + 5, int(first_pt[1]) + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone_color, 1)

        # Broadcast frame & telemetry over WebSocket
        broadcast_frame(camera_id, rendered_frame, detections, alerts, stream_telemetry)
