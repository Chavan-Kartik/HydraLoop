"""The command-center backend.

REST endpoints read the on-disk ledger; the WebSocket endpoint streams a run's
arena events with resume-from-sequence and an honest drop-oldest indicator.
"""

from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..red.llm import request_path_client
from . import harden as harden_module
from . import lab as lab_module
from . import ledger_source as src
from .hub import EventHub

app = FastAPI(title="HydraLoop Command Center", version="1.0")

# Local dev on any port, plus Vercel deployments including preview builds.
#
# The port has to be a wildcard: `next dev` silently moves to 3001, then 3002,
# when 3000 is already held by an earlier dev server. Pinning 3000 means the
# preflight for the JSON POST routes is rejected with a 400, which surfaces in
# the console as "the API is not running" while the GET routes keep returning
# 200, because simple requests are not preflighted. That is a confusing hour.
_ORIGIN_REGEX = r"http://(?:localhost|127\.0\.0\.1):\d+|https://[\w-]+(?:\.[\w-]+)*\.vercel\.app"

# Anything else (a custom domain, say) has to be named at runtime. Without it the
# browser blocks every call and the console falls back to its seeded snapshot,
# which looks like a working demo but is not talking to the backend at all.
_EXTRA_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("HYDRALOOP_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_EXTRA_ORIGINS,
    allow_origin_regex=_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MAX_TICK_MS = 2000
_RUN_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hydraloop-loop")
_JOBS: dict[str, dict] = {}

_ROOT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>HydraLoop API</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 40rem;
           margin: 12vh auto; padding: 0 1.5rem; color: #0b1220; line-height: 1.5; }
    a { color: #4f46e5; }
    code { background: #eef1f7; padding: 0.1rem 0.35rem; border-radius: 4px; }
  </style>
</head>
<body>
  <p>This is the <strong>HydraLoop API</strong>, not the UI.</p>
  <p>Open the command center at
     <a href="http://127.0.0.1:3000">http://127.0.0.1:3000</a>
     after starting it with <code>cd ui; npm run dev</code>.</p>
  <p>Health check: <a href="/api/health">/api/health</a></p>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Browser landing: this port is the API, the UI lives on :3000."""
    return _ROOT_HTML


@app.get("/api/health")
def health() -> dict:
    runs = src.list_runs()
    client = request_path_client()
    return {
        "status": "ok",
        "runs": len(runs),
        # Whether Identify will use a model or the keyword mapper on this
        # deployment. Reports configuration, not reachability: a wrong key still
        # reads as configured until the first call fails and the guard trips.
        "llm": {
            "configured": client is not None,
            "degraded": bool(getattr(client, "tripped", False)),
        },
    }


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


@app.get("/api/threats")
def threats() -> dict:
    """The abstracted threat catalog grouped by family (not run-specific)."""
    return src.threat_catalog()


@app.get("/api/lineage/{run_id}")
def lineage(run_id: str) -> dict:
    return src.genome_lineage(run_id)


@app.get("/api/investigations/{run_id}")
def investigations(run_id: str) -> dict:
    return src.investigations(run_id)


@app.get("/api/governance/{run_id}")
def governance(run_id: str) -> dict:
    """Recompute the hash chain and report tamper-evidence for the run's ledger."""
    return src.verify_ledger(run_id)


@app.get("/api/kpis/{run_id}")
def kpis(run_id: str) -> dict:
    return src.kpis(run_id)


@app.get("/api/strategist/{run_id}")
def strategist(run_id: str) -> dict:
    """The GenAI red-team strategist's audit: proposals, accepts, refusals, samples."""
    return src.strategist(run_id)


@app.get("/api/data-benchmark/{run_id}")
def data_benchmark(run_id: str) -> dict:
    """Fidelity vs a real/shifted reference: discriminator AUC, marginals, TSTR/TRTS."""
    return src.data_benchmark(run_id)


@app.get("/api/lab/presets")
def lab_presets() -> dict:
    return {"presets": [{"id": k, "text": v} for k, v in lab_module.PRESETS.items()]}


class LabBody(BaseModel):
    text: str = Field(..., min_length=12, max_length=600)


@app.post("/api/lab")
def lab(body: LabBody) -> dict:
    """Type a threat. Get Identify -> Generate -> Simulate -> Detect on one payload."""
    try:
        return lab_module.run_lab(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/lab/stream")
def lab_stream(body: LabBody):
    """Same as POST /api/lab, but each pipeline stage is flushed as NDJSON."""

    def gen():
        try:
            for event in lab_module.iter_lab(body.text):
                yield json.dumps(event, default=str) + "\n"
        except ValueError as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"
        except Exception as exc:  # noqa: BLE001 — surface to the UI
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/harden/stream")
def harden_stream(body: LabBody):
    """The closed loop on demand: let the attack escape, harden, then re-attack.

    Streams NDJSON so the UI can paint the incumbent, the escape, the retrain, the
    gauntlet verdict and the re-attack result as each one is computed.
    """

    def gen():
        try:
            for event in harden_module.iter_harden(body.text):
                yield json.dumps(event, default=str) + "\n"
        except Exception as exc:  # noqa: BLE001 -- surface to the UI, never 500 mid-stream
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.get("/api/lab/latest")
def lab_latest() -> dict:
    data = lab_module.load_latest_lab()
    if not data:
        raise HTTPException(status_code=404, detail="no lab run yet — open Lab and press Run")
    return data


@app.post("/api/run")
def run_coevolution(generations: int = 3) -> dict:
    """Start a short co-evolution run in the background and return its id immediately.

    The UI streams events as the ledger grows. Uses ``configs/live.yaml`` so a
    demo finishes in tens of seconds, not minutes.
    """
    import datetime as dt

    gens = max(1, min(int(generations), 5))
    run_id = dt.datetime.now().strftime("arena_%Y%m%d_%H%M%S")
    _JOBS[run_id] = {"status": "queued", "error": None}
    _RUN_POOL.submit(_execute_run, run_id, gens)
    return {
        "run_id": run_id,
        "generations": gens,
        "status": "queued",
        "note": "computing in background; poll GET /api/run/{run_id}",
    }


@app.get("/api/run/{run_id}")
def run_status(run_id: str) -> dict:
    job = _JOBS.get(run_id) or {"status": "unknown", "error": None}
    entries = src.load_ledger_entries(run_id)
    return {
        "run_id": run_id,
        "status": job.get("status", "unknown"),
        "error": job.get("error"),
        "generations_done": len(entries),
        "event_count": len(src.arena_events(run_id)),
    }


def _execute_run(run_id: str, generations: int) -> None:
    from ..config import load_config
    from ..loop.orchestrator import run_loop
    from ..paths import CONFIGS_DIR

    _JOBS[run_id] = {"status": "running", "error": None}
    try:
        cfg = load_config(CONFIGS_DIR / "live.yaml")
        run_loop(cfg, run_id, generations=generations)
        _JOBS[run_id] = {"status": "done", "error": None}
    except Exception as exc:  # noqa: BLE001 — surface to the UI, do not crash the API
        _JOBS[run_id] = {"status": "error", "error": str(exc)}


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
