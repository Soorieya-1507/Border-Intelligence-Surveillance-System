import numpy as np
import time
from app.core.video.stream_health import StreamHealthMonitor

def test_stream_health_black_screen():
    monitor = StreamHealthMonitor("cam_test")
    black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    monitor.record_input_frame(black_frame, time.time())
    assert monitor.status == "BLACK_SCREEN"

def test_stream_health_healthy_frame():
    monitor = StreamHealthMonitor("cam_test")
    # Random noise frame (high variance, bright mean)
    np.random.seed(42)
    random_frame = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    
    monitor.record_input_frame(random_frame, time.time())
    assert monitor.status == "HEALTHY"

def test_stream_health_fps():
    monitor = StreamHealthMonitor("cam_test")
    now = time.time()
    monitor.input_frame_times = [now + i * 0.1 for i in range(10)]
    
    fps = monitor.get_input_fps()
    assert 8.0 <= fps <= 12.0
