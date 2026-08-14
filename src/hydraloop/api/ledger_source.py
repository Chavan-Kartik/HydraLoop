"""Read runs from disk and project the ledger into arena events and scoreboard series.

Everything the UI renders comes from a real ``generation_ledger.jsonl`` under
``reports/runs/<run_id>/``. There are no fixtures; an empty runs directory yields
empty payloads, which the UI renders as its empty state.
"""

from __future__ import annotations

from pathlib import Path

from ..loop.ledger import GenerationLedger
from ..paths import EXAMPLES_DIR, RUNS_DIR


def _candidate_dirs() -> list[Path]:
    dirs: list[Path] = []
    for base in (RUNS_DIR, EXAMPLES_DIR):
        if base.exists():
            dirs.extend(p for p in base.iterdir() if p.is_dir())
    return dirs


def list_runs() -> list[dict]:
    runs = []
    for d in _candidate_dirs():
        ledger_path = d / "generation_ledger.jsonl"
        if not ledger_path.exists():
            continue
        ledger = GenerationLedger.load(ledger_path)
        runs.append(
            {
                "run_id": d.name,
                "source": d.parent.name,
                "generations": len(ledger.entries),
                "head_hash": ledger.head_hash,
                "mtime": ledger_path.stat().st_mtime,
            }
        )
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs


def resolve_run(run_id: str | None) -> Path | None:
    if run_id:
        for d in _candidate_dirs():
            if d.name == run_id and (d / "generation_ledger.jsonl").exists():
                return d
        return None
    runs = list_runs()
    if not runs:
        return None
    top = runs[0]["run_id"]
    return resolve_run(top)


def load_ledger_entries(run_id: str) -> list[dict]:
    d = resolve_run(run_id)
    if d is None:
        return []
    ledger = GenerationLedger.load(d / "generation_ledger.jsonl")
    return [e["payload"] for e in ledger.entries]


def scoreboard_series(run_id: str) -> dict:
    """Per-generation series for Recharts: escape rate, archive recall, gauntlet log."""
    entries = load_ledger_entries(run_id)
    points = []
    gauntlet_log = []
    for e in entries:
        points.append(
            {
                "generation": e["generation"],
                "escape_rate": e.get("escape_rate", 0.0),
                "escapes": e.get("escapes", 0),
                "candidate_archive_recall": e.get("candidate_archive_recall", 0.0),
                "incumbent_archive_recall": e.get("incumbent_archive_recall", 0.0),
                "promoted": e.get("promoted", False),
            }
        )
        for ev in e.get("gate_events", []):
            gauntlet_log.append({"generation": e["generation"], **ev})
    return {"run_id": run_id, "points": points, "gauntlet_log": gauntlet_log}


def arena_events(run_id: str) -> list[dict]:
    """Flatten the ledger into a ticker of arena events, each order-stable.

    One generation becomes: a generation banner, one event per escape cluster
    (red side), one event per gauntlet decision (blue side), and a summary.
    """
    entries = load_ledger_entries(run_id)
    events: list[dict] = []

    def push(kind: str, generation: int, text: str, data: dict) -> None:
        events.append({"type": kind, "generation": generation, "text": text, "data": data})

    for e in entries:
        g = e["generation"]
        push("generation_start", g, f"Generation {g} begins", {"n_genomes": e.get("n_genomes", 0)})
        for c in e.get("escape_clusters", []):
            push(
                "escape",
                g,
                f"Escape mode {c['dominant_attack_id']} x{c['size']}",
                c,
            )
        for ev in e.get("gate_events", []):
            push("gauntlet", g, ev.get("result", ""), ev)
        push(
            "generation_summary",
            g,
            f"escape_rate={e.get('escape_rate', 0.0)} promoted={e.get('promoted', False)}",
            {
                "escape_rate": e.get("escape_rate", 0.0),
                "escapes": e.get("escapes", 0),
                "promoted": e.get("promoted", False),
                "candidate_archive_recall": e.get("candidate_archive_recall", 0.0),
            },
        )
    return events
