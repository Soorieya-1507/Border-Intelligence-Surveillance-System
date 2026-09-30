# IBVAP Phase 0: Repository Audit Report

## 1. Current State Summary
The repository currently implements a functioning Phase 1 MVP that successfully ingests a single MP4 test video, performs YOLOv8n object detection and tracking, evaluates hardcoded virtual fence/loitering rules, and broadcasts the annotated frames and text alerts over WebSockets to a web dashboard.

While this proves the end-to-end pipeline, the current architecture is highly monolithic and violates several scalability and modularity principles required for the subsequent SIH 26187 roadmap phases.

---

## 2. Component Analysis

### A. Stream Architecture & Video Transport
- **Current Implementation**: `backend/app/core/stream_manager.py` handles video capture (`cv2.VideoCapture`) within a single background thread. Frames are processed sequentially and broadcast to clients as Base64-encoded JPEGs via `ws_telemetry.py`.
- **Missing / Broken**:
  - No reconnect logic for RTSP stream failures.
  - No frame dropping or low-latency mechanisms if the consumer/AI is too slow.
  - No stream health monitoring or FPS telemetry exposed.
  - Hardcoded to a single logical camera (`cam_01_alpha`).
- **Risky Assumptions**: Assumes the stream is always perfect. If `cv2.read()` fails, it just loops the test video (acceptable for MVP, unacceptable for Phase 1B).

### B. Detector & AI Inference
- **Current Implementation**: `backend/app/core/detector.py` uses Ultralytics YOLOv8n (`model.track()`).
- **Missing / Broken**:
  - Inference runs unconditionally on every single frame, which will bottleneck on edge devices.
  - No model registry or device selection (CPU/OpenVINO).
  - ROI-aware processing and frame skipping are missing.
- **Technical Debt**: The tracking algorithm (ByteTrack) is completely encapsulated inside YOLO, making it difficult to extract independent track lifecycles or swap the detector backend without losing tracking.

### C. Tracker & Trajectory Management
- **Current Implementation**: Detections with `track_id`s are returned by YOLO. `stream_manager.py` natively maintains a dictionary (`tracks_history`) to store the last 30 centroids.
- **Missing / Broken**:
  - No dedicated `trajectory_manager.py`.
  - Velocity, directionality, and track lifecycle (occlusion/disappearance) are not robustly modeled outside of the basic YOLO tracking.
- **Technical Debt**: Storing track history inside the video stream manager violates the Single Responsibility Principle.

### D. Zone Policy & Loitering Engine
- **Current Implementation**: Configured via `config.py` with hardcoded polygons. `analytics/virtual_fence.py` uses `cv2.pointPolygonTest`. `analytics/loitering.py` measures basic dwell time.
- **Missing / Broken**:
  - No dynamic polygon editing from the frontend.
  - Directional policy (INBOUND/OUTBOUND) relies on a rudimentary previous/current centroid check, which is susceptible to jitter.
  - Missing proper debounce/hysteresis for line fences.

### E. Event Fusion & Risk Engine
- **Current Implementation**: `risk_engine.py` applies a linear scoring matrix. Alerts are generated directly in the `StreamManager` loop.
- **Missing / Broken**:
  - No `Event Fusion Engine` (Phase 12).
  - Incidents are isolated to single rule triggers rather than correlated events.

### F. Frontend Dashboard
- **Current Implementation**: Single HTML file with Tailwind CSS and Vanilla JS WebSocket client.
- **Missing / Broken**:
  - UI is hardcoded for a single feed layout.
  - No telemetry (FPS, latency, camera health) displayed.
  - Missing interactive elements (draw zones, click replays).

---

## 3. Gap Report vs SIH Requirements
| Requirement | Current Status | Notes |
| :--- | :--- | :--- |
| **Edge-first modularity** | Partially Implemented | Exists locally, but deeply coupled. |
| **Conditional Inference** | Missing | Models run 100% of frames. |
| **Camera Resilience** | Missing | `VideoCapture` fails silently on network drop. |
| **Explainable Incidents** | Implemented | Risk Engine correctly outputs `risk_factors`. |
| **Confidence-aware Auth** | Missing | No Face/ANPR pipelines exist yet. |
| **Configurable Deployments** | Partially Implemented | Hardcoded in `config.py`, needs YAML profiles. |

---

## 4. Proposed Phase 1B Implementation Plan

To establish the **Camera / Video Foundation**, we must decouple the `StreamManager` from the analytics layer. 

**Files to Create/Modify**:
1. **Create** `backend/app/core/video/frame_buffer.py`: Thread-safe queue to handle asynchronous frame dropping and low-latency access.
2. **Create** `backend/app/core/video/stream_health.py`: Monitor FPS, jitter, and dropped frames.
3. **Create** `backend/app/core/video/frame_gate.py`: Controls which frames get passed to the AI (enabling frame-skipping and conditional inference later).
4. **Modify** `backend/app/core/video/stream_manager.py` (Move & Refactor): Remove YOLO and Analytics from this file. It should ONLY handle video ingestion, RTSP reconnects, and pushing frames to the `frame_buffer`.
5. **Modify** `backend/app/main.py`: Update stream initialization to use the new modular video pipeline and support multiple logical cameras.
6. **Modify** `frontend/static/js/app.js`: Add basic telemetry display (FPS, Drop rate) based on WS events.

**Conclusion**: The repository provides an excellent working baseline. Proceeding with Phase 1B will refactor the stream ingestion to be production-ready and resilient to real-world edge networking conditions.
