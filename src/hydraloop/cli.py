"""HydraLoop command-line entry point.

This is the single source of truth for running the system. ``Makefile`` and
``make.ps1`` delegate here so that a clean-machine ``make demo`` and the Windows
``make.ps1 demo`` target run identical code.
"""

from __future__ import annotations

import datetime as _dt

import typer

from .config import load_config
from .manifest import write_manifest
from .paths import ensure_dirs, run_dir

app = typer.Typer(add_completion=False, help="HydraLoop control plane.")


def _new_run_id() -> str:
    return _dt.datetime.now().strftime("run_%Y%m%d_%H%M%S")


@app.command()
def manifest(config: str = typer.Option(None, help="Path to a config YAML.")) -> None:
    """Emit a reproducibility manifest for the current configuration."""
    ensure_dirs()
    cfg = load_config(config)
    run_id = _new_run_id()
    path = write_manifest(run_dir(run_id), cfg, run_id)
    typer.echo(f"Run manifest written to {path}")


@app.command()
def twin(
    config: str = typer.Option(None, help="Path to a config YAML."),
    events: int = typer.Option(0, help="Override legitimate event target (0 = config)."),
    run_id: str = typer.Option(None, help="Reuse an existing run id."),
) -> None:
    """Generate legitimate synthetic payment traffic (Phase 1)."""
    from .twin.run import generate_legit_traffic

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = generate_legit_traffic(cfg, rid, event_target=events or None)
    typer.echo(f"Legit traffic written to {out}")


@app.command()
def attack(
    config: str = typer.Option(None),
    run_id: str = typer.Option(None),
) -> None:
    """Execute catalog attack genomes inside the twin (Phase 3)."""
    from .red.run import run_static_attacks

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = run_static_attacks(cfg, rid)
    typer.echo(f"Adversarial dataset written to {out}")


@app.command()
def train(
    config: str = typer.Option(None),
    run_id: str = typer.Option(None),
) -> None:
    """Train the blue-team baseline and emit the metrics report (Phase 4)."""
    from .blue.run import train_baseline

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = train_baseline(cfg, rid)
    typer.echo(f"Metrics report written to {out}")


@app.command()
def stack(
    config: str = typer.Option(None),
    run_id: str = typer.Option(None),
) -> None:
    """Train the deep defence stack and emit the ablation report (Phase 8)."""
    from .blue.stack_run import train_defense_stack

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = train_defense_stack(cfg, rid)
    typer.echo(f"Defence stack report written to {out}")


@app.command()
def loop(
    config: str = typer.Option(None),
    generations: int = typer.Option(0, help="Override generation count (0 = config)."),
    run_id: str = typer.Option(None),
) -> None:
    """Run the co-evolution loop with the regression gauntlet (Phase 6)."""
    from .loop.orchestrator import run_coevolution

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = run_coevolution(cfg, rid, generations=generations or None)
    typer.echo(f"Generation ledger written to {out}")


@app.command()
def evaluate(
    config: str = typer.Option(None),
    run_id: str = typer.Option(None),
) -> None:
    """Run the evaluation rigour suite: LOFO, zero-day, drift, fidelity, tornado (Phase 10)."""
    from .evaluation.run import run_evaluation

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = run_evaluation(cfg, rid)
    typer.echo(f"Evaluation report written to {out}")


@app.command()
def evolve(
    config: str = typer.Option(None),
    generations: int = typer.Option(15, help="Co-evolution generations (Gate G4 needs 15+)."),
    llm: str = typer.Option("none", help="GenAI strategist provider: none | ollama."),
    llm_model: str = typer.Option("llama3.2", help="Local model name for the strategist."),
    llm_base_url: str = typer.Option("http://localhost:11434", help="Ollama base URL."),
    run_id: str = typer.Option(None),
) -> None:
    """Run red-team economics + quality-diversity search vs the live policy (Phase 9).

    Pass ``--llm ollama`` to drive the red team with a local language model
    (schema-validated, offline). Without it, a deterministic planner is used, so
    the run never depends on a model being present.
    """
    from .red.coevolution import run_coevolution_economics

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = run_coevolution_economics(
        cfg, rid, generations=generations,
        llm_provider=llm, llm_model=llm_model, llm_base_url=llm_base_url,
    )
    typer.echo(f"Co-evolution economics written to {out}")


@app.command()
def discover(
    text: str = typer.Argument(..., help="Abstract description of an emerging fraud trend."),
    llm: str = typer.Option("none", help="GenAI mapper provider: none | ollama."),
    llm_model: str = typer.Option("llama3.2", help="Local model name."),
    run_id: str = typer.Option(None),
) -> None:
    """Identify: map an emerging-threat writeup into a simulatable attack genome.

    Turns a paragraph of abstract fraud intel into a schema-valid attack genome the
    twin can run - discovery, not a hand-written catalog entry. Uses a local model
    when ``--llm ollama`` is set, otherwise a deterministic keyword mapper.
    """
    import json as _json

    import numpy as _np

    from .red.discover import discover_threat
    from .red.llm import make_llm_client

    ensure_dirs()
    rid = run_id or _new_run_id()
    client = make_llm_client(llm, llm_model)
    result = discover_threat(text, _np.random.default_rng(0), llm=client)
    out = run_dir(rid) / "discovered_threat.json"
    out.write_text(_json.dumps(result, indent=2), encoding="utf-8")
    typer.echo(f"Discovered '{result['attack_name']}' -> family={result['family']} "
               f"(method={result['method']}), genome {result['genome_id']}")
    typer.echo(f"  {result['brief']}")
    typer.echo(f"Written to {out}")


@app.command()
def bench(
    config: str = typer.Option(None),
    preset: str = typer.Option(None, help="Built-in dataset: sparkov | paysim | creditcard."),
    csv: str = typer.Option(None, help="External transaction CSV to benchmark against."),
    amount_col: str = typer.Option("amount", help="External amount column."),
    timestamp_col: str = typer.Option("timestamp", help="External timestamp column."),
    fraud_col: str = typer.Option("is_fraud", help="External fraud-label column."),
    amount_is_minor: bool = typer.Option(False, help="External amounts are already in minor units."),
    run_id: str = typer.Option(None),
) -> None:
    """Benchmark synthetic traffic against a reference for fidelity + TSTR/TRTS.

    ``--preset sparkov`` (or paysim/creditcard) benchmarks against a real public
    dataset placed under ``data/external/<preset>.csv``. With neither preset nor
    ``--csv`` it runs synthetic-shift mode. If a preset file is missing it degrades
    gracefully to synthetic shift so the demo never breaks.
    """
    from .evaluation.data_adapter import ColumnMap, run_data_benchmark

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    colmap = None if preset else ColumnMap(
        amount=amount_col,
        timestamp=timestamp_col,
        is_fraud=fraud_col,
        amount_is_minor=amount_is_minor,
    )
    report = run_data_benchmark(
        cfg, external_csv=csv, colmap=colmap, out_dir=run_dir(rid), preset=preset
    )
    auc = report.get("discriminator_auc")
    typer.echo(f"Data benchmark ({report['mode']}) written to {run_dir(rid)}")
    if report.get("note"):
        typer.echo(f"  note: {report['note']}")
    typer.echo(f"  discriminator AUC: {auc} ({report.get('interpretation', '')})")


@app.command()
def demo(config: str = typer.Option("configs/experiments/demo.yaml")) -> None:
    """End-to-end smoke run: manifest, twin, attacks, baseline, short loop."""
    from .loop.orchestrator import run_coevolution

    ensure_dirs()
    cfg = load_config(config)
    rid = _new_run_id()
    write_manifest(run_dir(rid), cfg, rid)
    out = run_coevolution(cfg, rid, generations=cfg.simulation.generations)
    typer.echo(f"Demo complete. Ledger at {out}")


@app.command()
def api(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Launch the FastAPI + WebSocket command-center backend (Phase 7)."""
    import uvicorn

    uvicorn.run("hydraloop.api.app:app", host=host, port=port, reload=False)


def main() -> None:
    app()
