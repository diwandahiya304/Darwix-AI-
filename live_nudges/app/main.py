"""FastAPI server: WebSocket delivery channel + a minimal live dashboard
(CLAUDE.md §5 Q4: "dashboard, WebSocket, webhook, polling API, or CLI" —
this implements two of the five). `POST /start` runs one scenario's real
audio through the real pipeline (app/pipeline.py) on a background
thread, broadcasting every transcript segment, nudge, and suppression
decision to any connected `/ws` client in real time as the call plays.

The pipeline is synchronous by design (see app/broadcaster.py's
docstring) — this module is the only place that bridges it into
FastAPI's asyncio world.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from live_nudges.app.broadcaster import Broadcaster
from live_nudges.app.controller import SuppressionEvent
from live_nudges.app.models import Nudge, TranscriptSegment
from live_nudges.app.pipeline import run_call
from live_nudges.app.semantic import embed_for_dedup
from live_nudges.app.settings import REPO_ROOT, get_settings

app = FastAPI(title="live_nudges dashboard + WebSocket API")

_settings = get_settings()
_broadcaster = Broadcaster()
_AUDIO_DIR = REPO_ROOT / "recordings" / "live_nudges" / "audio"
_DASHBOARD_HTML = REPO_ROOT / "live_nudges" / "static" / "dashboard.html"

_state_lock = threading.Lock()
_running_call_id: str | None = None


class StartCallRequest(BaseModel):
    scenario_id: str
    speed: float = 1.0


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(str(_DASHBOARD_HTML))


@app.post("/start")
def start_call(request: StartCallRequest) -> JSONResponse:
    global _running_call_id
    audio_path = _AUDIO_DIR / f"{request.scenario_id}.wav"
    if not audio_path.exists():
        return JSONResponse(
            {"error": f"no audio for scenario {request.scenario_id!r} — run `make q4-generate-audio` first"},
            status_code=404,
        )

    with _state_lock:
        if _running_call_id is not None:
            return JSONResponse({"error": f"call {_running_call_id!r} already running"}, status_code=409)
        _running_call_id = request.scenario_id

    def _on_segment(segment: TranscriptSegment) -> None:
        _broadcaster.publish({"type": "segment", "data": segment.model_dump(mode="json")})

    def _on_nudge(nudge: Nudge) -> None:
        _broadcaster.publish({"type": "nudge", "data": nudge.model_dump(mode="json")})

    def _on_suppressed(event: SuppressionEvent) -> None:
        _broadcaster.publish({
            "type": "suppressed",
            "data": {"topic": event.signal.topic, "reason": event.reason, "confidence": event.signal.confidence},
        })

    def _run() -> None:
        global _running_call_id
        try:
            run_call(
                audio_path, call_id=request.scenario_id, settings=_settings, speed=request.speed,
                embed_fn=embed_for_dedup, on_segment=_on_segment, on_nudge=_on_nudge,
                on_suppressed=_on_suppressed,
            )
        finally:
            _broadcaster.publish({"type": "call_ended", "data": {"scenario_id": request.scenario_id}})
            with _state_lock:
                _running_call_id = None

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"status": "started", "scenario_id": request.scenario_id})


@app.get("/scenarios")
def list_scenarios() -> JSONResponse:
    if not _AUDIO_DIR.exists():
        return JSONResponse([])
    return JSONResponse(sorted(p.stem for p in _AUDIO_DIR.glob("*.wav")))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    subscriber_queue = _broadcaster.subscribe()
    try:
        while True:
            event = await asyncio.to_thread(subscriber_queue.get)
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        _broadcaster.unsubscribe(subscriber_queue)
