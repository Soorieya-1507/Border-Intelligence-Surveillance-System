import time

class LoiteringEngine:
    def __init__(self):
        # track_id -> time of entry
        self.entry_times = {}
        # track_id -> total dwell time
        self.dwell_times = {}
        
    def update(self, track_id: int, is_inside: bool, dt: float) -> float:
        """
        Update the loitering state for a track.
        Returns the current dwell time in seconds.
        """
        if is_inside:
            if track_id not in self.entry_times:
                self.entry_times[track_id] = time.time()
                self.dwell_times[track_id] = 0.0
            else:
                self.dwell_times[track_id] += dt
            return self.dwell_times[track_id]
        else:
            # If they leave, we reset
            if track_id in self.entry_times:
                del self.entry_times[track_id]
                del self.dwell_times[track_id]
            return 0.0
