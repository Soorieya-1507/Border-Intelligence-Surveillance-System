from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict
from enum import Enum
import time

class Direction(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    BIDIRECTIONAL = "BIDIRECTIONAL"

class DetectionSchema(BaseModel):
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    class_id: int
    class_name: str
    track_id: Optional[int] = None

class TrackSchema(BaseModel):
    track_id: int
    class_name: str
    history: List[Tuple[float, float]]  # List of centroids (x, y)
    velocity: Tuple[float, float] = (0.0, 0.0)
    dwell_time: float = 0.0

class RiskFactor(BaseModel):
    description: str
    score: int

class IncidentSchema(BaseModel):
    incident_id: str
    camera_id: str
    timestamp: float = Field(default_factory=time.time)
    entity_type: str
    track_id: Optional[int] = None
    rule_triggered: str
    risk_score: int
    risk_factors: List[RiskFactor]
    snapshot_path: Optional[str] = None
    clip_path: Optional[str] = None

class ZoneSchema(BaseModel):
    name: str
    polygon: List[Tuple[int, int]]  # x, y coordinates
    allowed_direction: Direction
    loitering_threshold_sec: float
