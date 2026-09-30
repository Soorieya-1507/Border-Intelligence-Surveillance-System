from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import cv2
import base64
import json
from typing import Dict, Any, List

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()
main_loop = None

@router.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()

def broadcast_frame(camera_id: str, frame: Any, detections: list, alerts: list, telemetry: Dict[str, Any] = None):
    if main_loop is None:
        return
        
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    if not ret:
        return
        
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    
    msg = {
        "type": "frame",
        "camera_id": camera_id,
        "image": jpg_as_text,
        "detections": len(detections),
        "alerts": alerts,
        "telemetry": telemetry or {}
    }
    
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg), main_loop)
    except Exception as e:
        pass

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
