import cv2
import numpy as np
from app.models.schemas import ZoneSchema, Direction

class VirtualFence:
    def __init__(self, zone: ZoneSchema):
        self.zone = zone
        self.polygon_pts = np.array(zone.polygon, np.int32)
        # Reshape for cv2.pointPolygonTest
        self.polygon_pts = self.polygon_pts.reshape((-1, 1, 2))
        
    def is_inside(self, point: tuple[float, float]) -> bool:
        """Returns True if point is inside the zone."""
        # pointPolygonTest returns +1 if inside, 0 if on contour, -1 if outside
        dist = cv2.pointPolygonTest(self.polygon_pts, point, False)
        return dist >= 0
        
    def check_crossing(self, prev_pt: tuple[float, float], curr_pt: tuple[float, float]) -> dict:
        """
        Checks if the trajectory crosses the fence boundary.
        Returns dict with status and direction.
        For MVP, we use simple point location. 
        """
        was_inside = self.is_inside(prev_pt)
        is_inside = self.is_inside(curr_pt)
        
        if not was_inside and is_inside:
            # Entering the zone (Inbound crossing)
            is_allowed = self.zone.allowed_direction in [Direction.INBOUND, Direction.BIDIRECTIONAL]
            return {"crossed": True, "type": "ENTER", "allowed": is_allowed}
            
        elif was_inside and not is_inside:
            # Exiting the zone (Outbound crossing)
            is_allowed = self.zone.allowed_direction in [Direction.OUTBOUND, Direction.BIDIRECTIONAL]
            return {"crossed": True, "type": "EXIT", "allowed": is_allowed}
            
        return {"crossed": False}
