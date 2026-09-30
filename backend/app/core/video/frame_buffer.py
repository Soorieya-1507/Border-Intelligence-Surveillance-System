import queue
import time
from typing import Optional, Tuple
import numpy as np

class FrameBuffer:
    """
    Thread-safe frame buffer that supports dropping stale frames 
    to enforce low-latency real-time video processing.
    """
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self._queue = queue.Queue(maxsize=max_size)
        self.total_received = 0
        self.total_dropped = 0

    def put(self, frame: np.ndarray, timestamp: float) -> bool:
        """
        Pushes a frame into the buffer. If the buffer is full,
        drops the oldest frame to maintain low latency.
        """
        self.total_received += 1
        dropped = False
        if self._queue.full():
            try:
                self._queue.get_nowait()
                self.total_dropped += 1
                dropped = True
            except queue.Empty:
                pass

        try:
            self._queue.put_nowait((frame, timestamp))
            return not dropped
        except queue.Full:
            self.total_dropped += 1
            return False

    def get_latest(self) -> Optional[Tuple[np.ndarray, float]]:
        """
        Retrieves the latest available frame, discarding any older accumulated frames.
        Returns (frame, timestamp) or None if buffer is empty.
        """
        latest = None
        while not self._queue.empty():
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                break
        return latest

    def get_nowait(self) -> Optional[Tuple[np.ndarray, float]]:
        """Retrieves a single frame in FIFO order without blocking."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def clear(self):
        """Clears the buffer contents."""
        with self._queue.mutex:
            self._queue.queue.clear()
            
    @property
    def size(self) -> int:
        return self._queue.qsize()
