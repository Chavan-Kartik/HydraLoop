"""Read runs from disk and project the ledger into arena events and scoreboard series.

Everything the UI renders comes from a real ``generation_ledger.jsonl`` under
``reports/runs/<run_id>/``. There are no fixtures; an empty runs directory yields
empty payloads, which the UI renders as its empty state.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..loop.ledger import GENESIS, GenerationLedger, _digest
from ..paths import EXAMPLES_DIR, REPORTS_DIR, RUNS_DIR


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


# --- Threat board -----------------------------------------------------------

_FAMILY_LABEL = {
    "synthetic_identity": "Synthetic Identity",
    "account_takeover": "Account Takeover",
    "social_engineering": "Social Engineering",
    "merchant_abuse": "Merchant Abuse",
    "card_testing": "Card Testing",
    "money_movement": "Money Movement",
    "agentic_commerce": "Agentic Commerce",
}


def threat_catalog() -> dict:
    """The whole abstracted threat catalog, grouped by family, for the board."""
    from ..catalog import load_catalog

    scenarios = load_catalog()
    threats = [
        {
            "attack_id": s.attack_id,
            "attack_name": s.attack_name,
            "family": s.family,
            "family_label": _FAMILY_LABEL.get(s.family, s.family),
            "risk_level": s.raw.get("risk_level", "unknown"),
            "evolvable": s.evolvable,
            "validation_status": s.raw.get("validation_status", "unverified_hypothetical"),
            "abstraction_level": s.raw.get("abstraction_level", ""),
            "payment_surface": s.raw.get("payment_surface", []),
            "behavioral_signals": s.raw.get("behavioral_signals", []),
            "mitigation_options": s.raw.get("mitigation_options", []),
        }
        for s in scenarios
    ]
    families: dict[str, int] = {}
    for t in threats:
        families[t["family"]] = families.get(t["family"], 0) + 1
    return {
        "threats": threats,
        "families": [
            {"family": f, "label": _FAMILY_LABEL.get(f, f), "count": c}
            for f, c in families.items()
        ],
        "total": len(threats),
    }


# --- Attack genome lineage --------------------------------------------------


def genome_lineage(run_id: str) -> dict:
    """Per-run lineage of escape modes, plus static genome briefs when present.

    Nodes are the distinct escaping genomes seen in the ledger, tagged with the
    generation and attack family; edges connect the same attack family across
    consecutive generations so the mutation trail is legible on stage.
    """
    d = resolve_run(run_id)
    briefs: dict[str, dict] = {}
    manifest: list[dict] = []
    if d is not None:
        gpath = d / "genomes.json"
        if gpath.exists():
            manifest = json.loads(gpath.read_text(encoding="utf-8"))
            for g in manifest:
                if g.get("genome_id"):
                    briefs[g["genome_id"]] = g
                if g.get("attack_id"):
                    briefs.setdefault(g["attack_id"], g)

    entries = load_ledger_entries(run_id)
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    last_by_attack: dict[str, str] = {}
    for e in entries:
        g = e["generation"]
        for c in e.get("escape_clusters", []):
            gid = c.get("dominant_genome", "")
            aid = c.get("dominant_attack_id", "")
            node_key = f"{g}:{gid}"
            if node_key not in seen:
                seen.add(node_key)
                brief = briefs.get(gid) or briefs.get(aid) or {}
                nodes.append(
                    {
                        "id": node_key,
                        "generation": g,
                        "genome_id": gid,
                        "attack_id": aid,
                        "family": brief.get("family", ""),
                        "size": c.get("size", 0),
                        "brief": brief.get("brief", ""),
                    }
                )
            if aid in last_by_attack:
                edges.append({"from": last_by_attack[aid], "to": node_key, "attack_id": aid})
            last_by_attack[aid] = node_key
    return {"run_id": run_id, "nodes": nodes, "edges": edges, "genomes": manifest}


# --- Investigation view -----------------------------------------------------


def _as_case_list(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("cases"), list):
        return raw["cases"]
    return []


def investigations(run_id: str) -> dict:
    """Flagged transactions with SHAP reason codes and a counterfactual."""
    d = resolve_run(run_id)
    cases: list[dict] = []
    source = run_id
    if d is not None:
        ipath = d / "investigations.json"
        if ipath.exists():
            cases = _as_case_list(json.loads(ipath.read_text(encoding="utf-8")))
    if not cases:
        lab_path = REPORTS_DIR / "lab" / "latest.json"
        if lab_path.exists():
            cases = _as_case_list(json.loads(lab_path.read_text(encoding="utf-8")))
            if cases:
                source = "lab_latest"
    if not cases:
        donor = EXAMPLES_DIR / "example_coevolution" / "investigations.json"
        if donor.exists():
            cases = _as_case_list(json.loads(donor.read_text(encoding="utf-8")))
            source = "example_coevolution"
    return {"run_id": run_id, "cases": cases, "source": source}


# --- Governance / audit -----------------------------------------------------


def verify_ledger(run_id: str) -> dict:
    """Recompute the hash chain and report tamper-evidence, without raising."""
    d = resolve_run(run_id)
    if d is None:
        return {"run_id": run_id, "verified": False, "reason": "run not found", "entries": []}
    path = d / "generation_ledger.jsonl"
    raw_entries = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    prev = GENESIS
    rows: list[dict] = []
    verified = True
    break_at: int | None = None
    for i, entry in enumerate(raw_entries):
        expected = _digest(entry["prev_hash"], entry["payload"])
        ok = entry["prev_hash"] == prev and entry["entry_hash"] == expected
        if not ok and verified:
            verified = False
            break_at = i
        payload = entry["payload"]
        rows.append(
            {
                "generation": payload.get("generation", i + 1),
                "entry_hash": entry["entry_hash"],
                "prev_hash": entry["prev_hash"],
                "promoted": payload.get("promoted", False),
                "escape_rate": payload.get("escape_rate", 0.0),
                "config_hash": payload.get("config_hash", ""),
                "link_ok": ok,
            }
        )
        prev = entry["entry_hash"]
    return {
        "run_id": run_id,
        "verified": verified,
        "break_at": break_at,
        "head_hash": raw_entries[-1]["entry_hash"] if raw_entries else GENESIS,
        "length": len(raw_entries),
        "entries": rows,
    }


# --- GenAI strategist -------------------------------------------------------


_STRATEGIST_PIPELINE = [
    {
        "verb": "Identify",
        "title": "Emerging GenAI fraud, as behaviour",
        "detail": "28 catalogued scenarios across 7 families, including agentic commerce. A writeup maps to a bounded genome — never a recipe.",
        "href": "/threats",
    },
    {
        "verb": "Generate",
        "title": "Schema-constrained proposals, then the twin",
        "detail": "The strategist only emits genome parameters. Invalid output is refused. The twin runs what survives against a live policy.",
        "href": "/lineage",
    },
    {
        "verb": "Defend",
        "title": "Escapes become the next training set",
        "detail": "The ensemble scores, the policy acts, immune memory retrains, and a gauntlet must pass before promotion.",
        "href": "/investigations",
    },
]


def _strategist_frame(run_id: str) -> dict:
    """Judge-facing fields that are always true of the lab, even with no LLM."""
    return {
        "run_id": run_id,
        "provider": "none",
        "model": None,
        "available": False,
        "proposals": 0,
        "accepted": 0,
        "refused": 0,
        "llm_authored": 0,
        "samples": [],
        "entries": [],
        "requires_api_key": False,
        "default_mode": "constrained_planner",
        "optional_provider": "ollama (local, no cloud key)",
        "guardrail": "schema-validated genome only; refusals logged; no free-text attacks",
        "pipeline": _STRATEGIST_PIPELINE,
    }


def strategist(run_id: str) -> dict:
    """The red-team GenAI strategist's audit for a run: proposals, accepts, refusals.

    The lab never needs a cloud API key. Default is a constrained planner; an
    optional local Ollama model can steer proposals, which are still schema-clamped.
    When this run has no audit file, we surface the committed evolve-example counts
    so the command center can still show the beat.
    """
    out = _strategist_frame(run_id)
    d = resolve_run(run_id)
    if d is not None:
        path = d / "strategist_audit.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["run_id"] = run_id
            out.update(data)
            out["source"] = run_id
        else:
            econ = d / "coevolution_economics.json"
            if econ.exists():
                summary = json.loads(econ.read_text(encoding="utf-8"))
                n = int(summary.get("audit_entries", 0))
                refused = int(summary.get("refusals", 0))
                out.update(
                    {
                        "proposals": n,
                        "accepted": max(0, n - refused),
                        "refused": refused,
                        "source": run_id,
                    }
                )
                nested = summary.get("strategist") or {}
                if nested:
                    out["provider"] = nested.get("provider", out["provider"])
                    out["model"] = nested.get("model")
                    out["available"] = bool(nested.get("available"))
                    out["llm_authored"] = int(nested.get("llm_authored", 0))

    if out["proposals"] == 0:
        evolve = EXAMPLES_DIR / "example_evolve" / "coevolution_economics.json"
        if evolve.exists():
            summary = json.loads(evolve.read_text(encoding="utf-8"))
            n = int(summary.get("audit_entries", 0))
            refused = int(summary.get("refusals", 0))
            out.update(
                {
                    "proposals": n,
                    "accepted": max(0, n - refused),
                    "refused": refused,
                    "source": "example_evolve",
                    "provider": "none",
                    "available": False,
                    "llm_authored": 0,
                }
            )
    out["requires_api_key"] = False
    out["pipeline"] = _STRATEGIST_PIPELINE
    out.setdefault("default_mode", "constrained_planner")
    out.setdefault(
        "optional_provider",
        "ollama (local, no cloud key)",
    )
    out.setdefault(
        "guardrail",
        "schema-validated genome only; refusals logged; no free-text attacks",
    )
    return out


# --- Data credibility benchmark ---------------------------------------------


def data_benchmark(run_id: str) -> dict:
    """The fidelity benchmark for a run, if a `data_benchmark.json` sits alongside."""
    d = resolve_run(run_id)
    if d is None:
        return {"run_id": run_id, "available": False}
    path = d / "data_benchmark.json"
    if not path.exists():
        return {"run_id": run_id, "available": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["run_id"] = run_id
    data["available"] = True
    return data


# --- KPI header -------------------------------------------------------------


def kpis(run_id: str) -> dict:
    """Headline numbers a judge reads in five seconds."""
    entries = load_ledger_entries(run_id)
    d = resolve_run(run_id)
    out: dict = {"run_id": run_id, "generations": len(entries)}
    if entries:
        first, last = entries[0], entries[-1]
        out["escape_rate_start"] = first.get("escape_rate", 0.0)
        out["escape_rate_end"] = last.get("escape_rate", 0.0)
        out["promotions"] = sum(1 for e in entries if e.get("promoted"))
        out["rollbacks"] = sum(
            1
            for e in entries
            for ev in e.get("gate_events", [])
            if str(ev.get("result", "")).startswith("REJECT")
        )
        out["total_escapes"] = sum(e.get("escapes", 0) for e in entries)
        out["best_archive_recall"] = max(
            (e.get("candidate_archive_recall", 0.0) for e in entries), default=0.0
        )
    # Attacker economics, when a co-evolution economics run sits alongside.
    if d is not None:
        econ = d / "coevolution_economics.json"
        if econ.exists():
            data = json.loads(econ.read_text(encoding="utf-8"))
            out["attacker_roi_start"] = data.get("roi_start")
            out["attacker_roi_end"] = data.get("roi_end")
            out["behavior_coverage_end"] = data.get("coverage_end")
            out["roi_collapsed"] = data.get("roi_collapsed")
    return out
