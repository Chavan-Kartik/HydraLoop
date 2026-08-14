"""The command-center backend.

REST endpoints read the on-disk ledger; the WebSocket endpoint streams a run's
arena events with resume-from-sequence and an honest drop-oldest indicator.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import ledger_source as src
from .hub import EventHub

app = FastAPI(title="HydraLoop Command Center", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_MAX_TICK_MS = 2000


@app.get("/api/health")
def health() -> dict:
    runs = src.list_runs()
    return {"status": "ok", "runs": len(runs)}


@app.get("/api/runs")
def runs() -> dict:
    return {"runs": src.list_runs()}


@app.get("/api/ledger/{run_id}")
def ledger(run_id: str) -> dict:
    return {"run_id": run_id, "entries": src.load_ledger_entries(run_id)}


@app.get("/api/scoreboard/{run_id}")
def scoreboard(run_id: str) -> dict:
    return src.scoreboard_series(run_id)


@app.get("/api/arena/{run_id}")
def arena(run_id: str) -> dict:
    """The full projected event list, for SSR and the offline pre-seeded cache."""
    return {"run_id": run_id, "events": src.arena_events(run_id)}


@app.post("/api/run")
def run_coevolution(generations: int = 5) -> dict:
    """Kick a short co-evolution run and return its id (runs in a worker thread)."""
    import datetime as dt

    from ..config import load_config
    from ..loop.orchestrator import run_loop

    run_id = dt.datetime.now().strftime("arena_%Y%m%d_%H%M%S")
    cfg = load_config()
    run_loop(cfg, run_id, generations=max(1, min(generations, 10)))
    return {"run_id": run_id, "generations": generations}


def _build_hub(run_id: str) -> EventHub:
    hub = EventHub()
    for event in src.arena_events(run_id):
        hub.publish(event)
    return hub


@app.websocket("/ws/arena/{run_id}")
async def ws_arena(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    try:
        since = int(websocket.query_params.get("since", "-1"))
    except ValueError:
        since = -1
    try:
        tick_ms = max(0, min(_MAX_TICK_MS, int(websocket.query_params.get("tick_ms", "250"))))
    except ValueError:
        tick_ms = 250

    hub = _build_hub(run_id)
    replay = hub.replay_since(since)
    if replay.dropped > 0:
        # The client fell behind the ring; tell it exactly what it missed.
        await websocket.send_json(
            {"type": "resync", "dropped": replay.dropped, "resume_from": hub.earliest_seq}
        )

    try:
        for item in replay.events:
            await websocket.send_json({"seq": item.seq, **item.event})
            if tick_ms:
                await asyncio.sleep(tick_ms / 1000.0)
        await websocket.send_json({"type": "complete", "head_seq": hub.next_seq - 1})
        # Keep the socket open so the client controls disconnect (resume works).
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
