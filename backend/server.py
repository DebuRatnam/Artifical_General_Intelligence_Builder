"""
server.py
Headless FastAPI backend for PIA (Physics-Informed Agents).

Ports the Streamlit `main_gui.py` backend (WorldModel state, serial
ingestion threads, VLM observe path, memory inspector, chat) into a
plain HTTP + WebSocket service so a separate Vite frontend can drive
the agent.

Endpoints:
    GET  /api/health         liveness + path/observation counters
    POST /api/observe        capture camera frame → world_model.observe
    GET  /api/memory         list every ObjectCard in long-term memory
    POST /api/chat           grounded chat via local Ollama model
    WS   /ws/telemetry       streams (ts, accel_g, fft_hz, tactile_state)

Run:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import os
import queue
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

# Make repo root importable so `from sensors...` etc. resolve no matter
# where uvicorn is launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import cv2
import ollama
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import agent_simulator as agent
from sensors.data_harvester import start as start_serial
from sensors.data_harvester import start_mock, token_queue
from perception.world_model import WorldModel


# ── Config (env-driven so the frontend doesn't need to send it) ──────────────
USE_MOCK    = os.getenv("PIA_USE_MOCK", "1") == "1"
SERIAL_PORT = os.getenv("PIA_SERIAL_PORT", "/dev/ttyUSB0")
BAUD_RATE   = int(os.getenv("PIA_BAUD_RATE", "460800"))
VLM_MODEL   = os.getenv("PIA_VLM_MODEL", "llava")
CHAT_MODEL  = os.getenv("PIA_CHAT_MODEL", "qwen2.5:3b")
MEMORY_PATH = os.getenv("PIA_MEMORY_PATH", "object_memory.db")
CAMERA_INDEX = int(os.getenv("PIA_CAMERA_INDEX", "0"))
WS_HZ        = float(os.getenv("PIA_WS_HZ", "40"))   # 30–60 Hz target


# ── Global state — survives across requests; never re-initialized ────────────
# The Streamlit version re-instantiated WorldModel on every session reload,
# losing the in-memory Scene. Here we keep one module-level singleton so
# the persistent scene + decay window survive every HTTP/WS hit.
world_model: Optional[WorldModel] = None
camera: Optional[cv2.VideoCapture] = None
_latest_accel: float = 0.0
_latest_fft: int = 0
_latest_ts: int = 0
_state_lock = threading.Lock()


# ── Lifespan: spawn harvester + agent threads once at startup ───────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global world_model, camera

    world_model = WorldModel(model_name=VLM_MODEL, memory_path=MEMORY_PATH)

    if USE_MOCK:
        start_mock(hz=100)
        print("[server] harvester: MOCK mode")
    else:
        start_serial(port=SERIAL_PORT, baud=BAUD_RATE)
        print(f"[server] harvester: serial {SERIAL_PORT} @ {BAUD_RATE}")

    # Tactile classifier + contact-event detector. Shares the world
    # model so contact spikes bootstrap object signatures into memory.
    agent.start(token_queue, memory=world_model.memory, world_model=world_model)

    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        print(f"[server] camera index {CAMERA_INDEX} unavailable — /api/observe will 503")

    yield

    if camera is not None:
        camera.release()
    world_model.memory.close()


app = FastAPI(title="PIA Server", lifespan=lifespan)


# ── CORS — Vite dev server defaults to :5173, allow common dev origins ──────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ─────────────────────────────────────────────────────────────────
class ObserveRequest(BaseModel):
    force_vlm: bool = False


class ChatRequest(BaseModel):
    prompt: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]


# ── Helpers ─────────────────────────────────────────────────────────────────
def _drain_queue_to_latest() -> None:
    """Drain pending serial tokens; keep newest accel/fft/ts under lock."""
    global _latest_accel, _latest_fft, _latest_ts
    drained = 0
    last = None
    while drained < 64:
        try:
            last = token_queue.get_nowait()
            drained += 1
        except queue.Empty:
            break
    if last is not None:
        with _state_lock:
            _latest_ts, _latest_accel, _latest_fft, _ = last


def _build_chat_context(wm: WorldModel, accel: float, fft: int) -> str:
    """Same RAG context the Streamlit chat used — ports main_gui.build_chat_context."""
    scene = wm.scene
    visible = list(scene.objects.keys()) or ["(nothing identified yet)"]
    sounds = [(s.label, s.freq_hz) for s in scene.audio_sources.values()] or [("(none)", 0)]
    mem_lines = []
    for c in wm.memory.all()[:25]:
        mem_lines.append(
            f"  • {c.label}: seen×{c.n_visual}, touched×{c.n_tactile} "
            f"(accel≈{c.tactile_accel_mean:.2f}g, fft≈{int(c.tactile_fft_mean)}Hz), "
            f"audio≈{c.audio_freq_hz}Hz"
        )
    mem_block = "\n".join(mem_lines) if mem_lines else "  (empty)"
    return (
        "You are an embodied perceptual agent. You have a camera, a glove-mounted "
        "IMU, and a microphone (FFT peak). Ground every answer in the data below; "
        "do not invent objects or sensor readings.\n\n"
        f"Currently visible objects: {visible}\n"
        f"Audio sources (label, freq Hz): {sounds}\n"
        f"Latest tactile sample: accel={accel:.3f}g, fft_peak={fft}Hz\n"
        f"Most recent tactile classification: {scene.last_tactile_label or '(none)'}\n\n"
        "Long-term memory (every object the agent has grounded):\n"
        f"{mem_block}\n"
    )


def _scene_payload(wm: WorldModel) -> dict:
    """JSON-safe snapshot of the current Scene for the frontend renderer."""
    scene = wm.scene
    return {
        "objects": [
            {
                "label": o.label, "x": o.x, "y": o.y,
                "icon": o.icon, "confidence": o.confidence,
                "last_seen": o.last_seen,
            }
            for o in scene.objects.values()
        ],
        "audio_sources": [
            {"label": s.label, "icon": s.icon, "freq_hz": s.freq_hz,
             "last_seen": s.last_seen}
            for s in scene.audio_sources.values()
        ],
        "hand": (
            {"x": scene.hand.x, "y": scene.hand.y, "last_seen": scene.hand.last_seen}
            if scene.hand else None
        ),
        "last_summary": scene.last_summary,
        "last_tactile_label": scene.last_tactile_label,
        "last_used_fast_path": scene.last_used_fast_path,
    }


# ── REST endpoints ──────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mock": USE_MOCK,
        "vlm_model": VLM_MODEL,
        "chat_model": CHAT_MODEL,
        "objects": len(world_model.scene.objects) if world_model else 0,
        "memory_size": len(world_model.memory.all()) if world_model else 0,
        "camera_ok": bool(camera and camera.isOpened()),
    }


@app.post("/api/observe")
def observe(req: ObserveRequest):
    if world_model is None:
        raise HTTPException(503, "world model not initialized")
    if camera is None or not camera.isOpened():
        raise HTTPException(503, "camera unavailable")

    ok, frame = camera.read()
    if not ok or frame is None:
        raise HTTPException(503, "camera frame read failed")

    _drain_queue_to_latest()
    with _state_lock:
        accel, fft = _latest_accel, _latest_fft

    scene = world_model.observe(
        frame=frame, accel_g=accel, fft_hz=fft, force_vlm=req.force_vlm,
    )
    return {
        "scene": _scene_payload(world_model),
        "telemetry": {"accel_g": accel, "fft_hz": fft},
        "summary": scene.last_summary,
    }


@app.get("/api/memory")
def memory():
    if world_model is None:
        raise HTTPException(503, "world model not initialized")
    cards = world_model.memory.all()
    return {
        "count": len(cards),
        "cards": [
            {
                "label": c.label,
                "description": c.description,
                "n_visual": c.n_visual,
                "n_tactile": c.n_tactile,
                "n_audio": c.n_audio,
                "tactile_accel_mean": c.tactile_accel_mean,
                "tactile_accel_std": c.tactile_accel_std,
                "tactile_fft_mean": c.tactile_fft_mean,
                "tactile_fft_std": c.tactile_fft_std,
                "audio_freq_hz": c.audio_freq_hz,
                "tactile_trained": c.tactile_trained,
                "first_seen": c.first_seen,
                "last_seen": c.last_seen,
            }
            for c in cards
        ],
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    if world_model is None:
        raise HTTPException(503, "world model not initialized")

    _drain_queue_to_latest()
    with _state_lock:
        accel, fft = _latest_accel, _latest_fft

    ctx = _build_chat_context(world_model, accel, fft)
    messages = [{"role": "system", "content": ctx}, *req.history,
                {"role": "user", "content": req.prompt}]
    try:
        resp = ollama.chat(model=CHAT_MODEL, messages=messages)
        reply = resp["message"]["content"]
    except Exception as e:
        raise HTTPException(502, f"chat model error: {e}")
    return {"reply": reply, "model": CHAT_MODEL}


# ── WebSocket telemetry stream ──────────────────────────────────────────────
@app.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket):
    """
    Push (ts, accel_g, fft_hz, tactile_state) at ~WS_HZ.

    Drains token_queue every tick; never blocks the asyncio loop on
    serial I/O (the harvester thread does that). The tactile state is
    pulled from agent_simulator's globals — set by its consumer loop.
    """
    await ws.accept()
    period = 1.0 / max(WS_HZ, 1.0)
    try:
        while True:
            _drain_queue_to_latest()
            with _state_lock:
                ts, accel, fft = _latest_ts, _latest_accel, _latest_fft

            await ws.send_json({
                "timestamp_ms": ts,
                "accel_g": accel,
                "fft_peak_hz": fft,
                "tactile": {
                    "label": agent.current_label,
                    "directive": agent.current_directive,
                    "distance_sigma": agent.current_distance,
                    "last_contact_ts": agent.last_contact_ts,
                },
                "server_time": time.time(),
            })
            await asyncio.sleep(period)
    except WebSocketDisconnect:
        return
    except Exception as e:
        print(f"[server] /ws/telemetry closed: {e}")
        try:
            await ws.close()
        except Exception:
            pass
