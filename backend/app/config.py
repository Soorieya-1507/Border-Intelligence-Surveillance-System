from app.models.schemas import ZoneSchema, Direction
from typing import Dict, List

class Settings:
    PROJECT_NAME = "IBVAP - Intelligent Border Video Analytics Platform"
    DEPARTMENT = "Ministry of Home Affairs / Sashastra Seema Bal (SSB)"
    DEPLOYMENT_PROFILE = "BOP Sector 12 - Indo-Nepal Frontier"
    
    # Global analytics thresholds
    LOITERING_GLOBAL_THRESHOLD = 4.0 # seconds
    
    # Camera Stream Definitions
    CAMERAS = {
        "cam_01_alpha": {
            "name": "CAM 01: BOP Alpha (North Perimeter)",
            "location": "Pillar 412/3 - Pedestrian Incursion Zone",
            "file": "border_post_alpha.mp4",
            "fps": 15.0,
            "zones": [
                ZoneSchema(
                    name="Red Border Perimeter",
                    polygon=[(60, 80), (60, 420), (320, 420), (320, 80)],
                    allowed_direction=Direction.OUTBOUND,
                    loitering_threshold_sec=3.0
                ),
                ZoneSchema(
                    name="Amber Buffer Zone",
                    polygon=[(340, 80), (340, 420), (600, 420), (600, 80)],
                    allowed_direction=Direction.BIDIRECTIONAL,
                    loitering_threshold_sec=6.0
                )
            ]
        },
        "cam_02_bravo": {
            "name": "CAM 02: BOP Bravo (Road Checkpost)",
            "location": "Highway Sector 9 - Strategic Vehicle Transit",
            "file": "border_road_vehicle.mp4",
            "fps": 15.0,
            "zones": [
                ZoneSchema(
                    name="Restricted Transit Corridor",
                    polygon=[(100, 150), (100, 680), (550, 680), (550, 150)],
                    allowed_direction=Direction.INBOUND,
                    loitering_threshold_sec=4.0
                ),
                ZoneSchema(
                    name="Checkpoint Perimeter",
                    polygon=[(580, 150), (580, 680), (1100, 680), (1100, 150)],
                    allowed_direction=Direction.BIDIRECTIONAL,
                    loitering_threshold_sec=8.0
                )
            ]
        }
    }
    
    # Risk weights for explainable heuristic scoring
    RISK_WEIGHTS = {
        "Base Intrusion": 40,
        "Loitering Exceeded": 25,
        "Night Hours": 20,
        "Wrong Direction": 30,
        "Vehicle Anomaly": 35
    }

settings = Settings()
