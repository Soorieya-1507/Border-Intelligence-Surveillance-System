import time
import cv2
import numpy as np

class FrameGate:
    """
    Controls frame pacing and conditional inference triggering
    to prevent hardware overload on edge deployments.
    """
    def __init__(self, target_analysis_fps: float = 15.0, enable_motion_gating: bool = False):
        self.target_analysis_fps = target_analysis_fps
        self.min_interval = 1.0 / target_analysis_fps if target_analysis_fps > 0 else 0.0
        self.last_analysis_time = 0.0
        self.enable_motion_gating = enable_motion_gating
        self.prev_motion_gray = None

    def should_process(self, frame: np.ndarray, timestamp: float) -> bool:
        """
        Determines whether the current frame should undergo full AI analysis.
        """
        now = time.time()
        
        # 1. FPS / Pacing Gating
        if (now - self.last_analysis_time) < self.min_interval:
            return False

        # 2. Optional Motion Gating (Skip static frames when no motion exists)
        if self.enable_motion_gating and frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if self.prev_motion_gray is not None:
                delta = cv2.absdiff(self.prev_motion_gray, gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_pixels = cv2.countNonZero(thresh)
                
                self.prev_motion_gray = gray
                # If less than 0.1% of frame pixels changed, skip heavy inference
                if motion_pixels < (frame.shape[0] * frame.shape[1] * 0.001):
                    return False
            else:
                self.prev_motion_gray = gray

        self.last_analysis_time = now
        return True
