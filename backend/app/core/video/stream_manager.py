import cv2
import threading
import time
import os
import numpy as np
from typing import Callable, Optional
from app.core.video.frame_buffer import FrameBuffer
from app.core.video.stream_health import StreamHealthMonitor
from app.core.video.frame_gate import FrameGate

class ResilientStreamManager:
    """
    Production-grade edge stream manager supporting RTSP, MP4, AVI, Webcams, 
    automatic reconnects, frame buffering, and health monitoring.
    """
    def __init__(self, camera_id: str, source_url: str, target_fps: float = 15.0):
        self.camera_id = camera_id
        self.source_url = source_url
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.reader_thread: Optional[threading.Thread] = None
        
        # Core components
        self.buffer = FrameBuffer(max_size=5)
        self.health = StreamHealthMonitor(camera_id=camera_id)
        self.gate = FrameGate(target_analysis_fps=target_fps)
        
        # Callbacks
        self.on_frame_callback: Optional[Callable] = None
        self.on_telemetry_callback: Optional[Callable] = None
        
        # Reconnect parameters
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 10.0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()

    def stop(self):
        self.is_running = False
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()

    def _open_capture(self) -> bool:
        """Opens VideoCapture supporting RTSP, integer webcams, or local files."""
        # Convert numeric string to integer for local webcam index
        source = self.source_url
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self.cap = cv2.VideoCapture(source)
        if self.cap and self.cap.isOpened():
            self.health.status = "HEALTHY"
            self.health.status_reason = "Stream connected"
            self.reconnect_delay = 1.0
            return True
        else:
            self.health.status = "DISCONNECTED"
            self.health.status_reason = f"Failed to connect to source {self.source_url}"
            return False

    def _reader_loop(self):
        """Dedicated thread loop for non-blocking frame ingestion and reconnects."""
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                if not self._open_capture():
                    time.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, self.max_reconnect_delay)
                    continue

            ret, frame = self.cap.read()
            timestamp = time.time()

            if not ret:
                # For video files, loop back to start for continuous testing
                if isinstance(self.source_url, str) and os.path.exists(self.source_url):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.01)
                    continue
                else:
                    # Stream dropped or ended (RTSP / webcam disconnect)
                    self.health.status = "DISCONNECTED"
                    self.health.status_reason = "Stream connection dropped"
                    if self.cap:
                        self.cap.release()
                    time.sleep(self.reconnect_delay)
                    continue

            # Record health metrics & push frame to buffer
            self.health.record_input_frame(frame, timestamp, self.buffer.total_dropped)
            self.buffer.put(frame, timestamp)

            # Check if frame gate allows AI processing
            if self.gate.should_process(frame, timestamp):
                start_time = time.time()
                if self.on_frame_callback:
                    self.on_frame_callback(self.camera_id, frame, timestamp, self.health.get_telemetry())
                analysis_latency = time.time() - start_time
                self.health.record_analysis_frame(analysis_latency)

            # Broadcast periodic telemetry
            if self.on_telemetry_callback:
                self.on_telemetry_callback(self.health.get_telemetry())

            # Yield slightly to avoid CPU spinning
            time.sleep(0.005)
