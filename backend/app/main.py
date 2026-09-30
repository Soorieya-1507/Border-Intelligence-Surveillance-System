from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import ws_telemetry
from app.core.video.stream_manager import ResilientStreamManager
from app.core.pipeline import AnalyticsPipeline
from app.config import settings
import os
import contextlib

streams = {}
pipeline = None

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = AnalyticsPipeline()
    samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/samples"))
    
    # Initialize all configured cameras from settings
    for cam_id, cam_cfg in settings.CAMERAS.items():
        video_path = os.path.join(samples_dir, cam_cfg["file"])
        if os.path.exists(video_path):
            manager = ResilientStreamManager(
                camera_id=cam_id,
                source_url=video_path,
                target_fps=cam_cfg.get("fps", 15.0)
            )
            manager.on_frame_callback = pipeline.process_frame
            manager.start()
            streams[cam_id] = manager
            print(f"[IBVAP Core] Started {cam_cfg['name']} on {video_path}")
        else:
            print(f"[IBVAP Core] Video file for {cam_id} not found at {video_path}")

    yield

    # Graceful shutdown
    for manager in streams.values():
        manager.stop()

app = FastAPI(
    title="IBVAP - Intelligent Border Video Analytics Platform",
    description="Ministry of Home Affairs / SSB Video Surveillance AI Engine",
    version="1.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_telemetry.router)

# Mount snapshots directory for evidence replay
snapshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/snapshots"))
os.makedirs(snapshots_dir, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=snapshots_dir), name="snapshots")

@app.get("/api/cameras")
async def get_cameras():
    return {
        "cameras": [
            {
                "id": cam_id,
                "name": cfg["name"],
                "location": cfg["location"],
                "status": streams[cam_id].health.status if cam_id in streams else "OFFLINE"
            }
            for cam_id, cfg in settings.CAMERAS.items()
        ]
    }

@app.get("/api/health")
async def health_check():
    return {"status": "HEALTHY", "platform": "IBVAP Edge AI", "department": settings.DEPARTMENT}

# Mount frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
