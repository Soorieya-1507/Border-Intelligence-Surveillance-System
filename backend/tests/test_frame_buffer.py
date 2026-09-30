import numpy as np
from app.core.video.frame_buffer import FrameBuffer

def test_frame_buffer_put_and_get():
    fb = FrameBuffer(max_size=3)
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    frame2 = np.ones((100, 100, 3), dtype=np.uint8)
    
    assert fb.put(frame1, 1.0) is True
    assert fb.put(frame2, 2.0) is True
    assert fb.size == 2
    
    latest = fb.get_latest()
    assert latest is not None
    assert latest[1] == 2.0
    assert fb.size == 0

def test_frame_buffer_overflow_drop():
    fb = FrameBuffer(max_size=2)
    f1 = np.zeros((10, 10, 3), dtype=np.uint8)
    f2 = np.ones((10, 10, 3), dtype=np.uint8)
    f3 = np.full((10, 10, 3), 2, dtype=np.uint8)
    
    fb.put(f1, 1.0)
    fb.put(f2, 2.0)
    # This should drop f1
    dropped = fb.put(f3, 3.0)
    
    assert fb.total_dropped == 1
    assert fb.size == 2
    
    val = fb.get_nowait()
    assert val[1] == 2.0 # f1 was dropped, so f2 is first
