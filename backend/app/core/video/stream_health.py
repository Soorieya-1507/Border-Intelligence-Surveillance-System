import time
import cv2
import numpy as np
from typing import Dict, Any

class StreamHealthMonitor:
    """
    Monitors camera health, frame quality, FPS, latency, 
    and anomaly states (black screen, frozen frame, blur).
    """
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        
        # FPS & Latency counters
        self.input_frame_times = []
        self.analysis_frame_times = []
        self.last_frame_timestamp = time.time()
        self.last_analysis_timestamp = time.time()
        self.latency_ms = 0.0
        self.dropped_frames = 0
        
        # Quality check states
        self.prev_frame_gray = None
        self.frozen_counter = 0
        self.status = "DISCONNECTED"
        self.status_reason = "Initialized"

    def record_input_frame(self, frame: np.ndarray, timestamp: float, dropped_count: int = 0):
        now = time.time()
        self.input_frame_times.append(now)
        self.last_frame_timestamp = timestamp
        self.dropped_frames = dropped_count
        
        # Keep window of last 60 frames for FPS calculation
        if len(self.input_frame_times) > 60:
            self.input_frame_times.pop(0)

        # Check visual quality
        self._analyze_quality(frame)

    def record_analysis_frame(self, latency_sec: float):
        now = time.time()
        self.analysis_frame_times.append(now)
        self.latency_ms = round(latency_sec * 1000, 1)
        if len(self.analysis_frame_times) > 60:
            self.analysis_frame_times.pop(0)

    def _analyze_quality(self, frame: np.ndarray):
        if frame is None or frame.size == 0:
            self.status = "DISCONNECTED"
            self.status_reason = "Empty frame received"
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Black frame detection
        mean_val = float(np.mean(gray))
        if mean_val < 5.0:
            self.status = "BLACK_SCREEN"
            self.status_reason = f"Low pixel brightness ({mean_val:.1f})"
            return

        # 2. Blur detection (Laplacian variance)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < 100.0:
            self.status = "BLURRED"
            self.status_reason = f"Low focus variance ({laplacian_var:.1f})"
            return

        # 3. Frozen frame detection
        if self.prev_frame_gray is not None and self.prev_frame_gray.shape == gray.shape:
            diff = cv2.absdiff(gray, self.prev_frame_gray)
            mean_diff = float(np.mean(diff))
            if mean_diff < 0.5:
                self.frozen_counter += 1
                if self.frozen_counter > 30: # ~1 second at 30fps
                    self.status = "FROZEN"
                    self.status_reason = "Static video feed detected"
                    return
            else:
                self.frozen_counter = 0

        self.prev_frame_gray = gray
        self.status = "HEALTHY"
        self.status_reason = "Normal operation"

    def get_input_fps(self) -> float:
        if len(self.input_frame_times) < 2:
            return 0.0
        elapsed = self.input_frame_times[-1] - self.input_frame_times[0]
        return round((len(self.input_frame_times) - 1) / max(elapsed, 0.001), 1)

    def get_analysis_fps(self) -> float:
        if len(self.analysis_frame_times) < 2:
            return 0.0
        elapsed = self.analysis_frame_times[-1] - self.analysis_frame_times[0]
        return round((len(self.analysis_frame_times) - 1) / max(elapsed, 0.001), 1)

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "status": self.status,
            "status_reason": self.status_reason,
            "input_fps": self.get_input_fps(),
            "analysis_fps": self.get_analysis_fps(),
            "dropped_frames": self.dropped_frames,
            "latency_ms": self.latency_ms,
            "last_frame_timestamp": round(self.last_frame_timestamp, 3)
        }
