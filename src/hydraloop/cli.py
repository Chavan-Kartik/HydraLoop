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
    run_id: str = typer.Option(None),
) -> None:
    """Run red-team economics + quality-diversity search vs the live policy (Phase 9)."""
    from .red.coevolution import run_coevolution_economics

    cfg = load_config(config)
    rid = run_id or _new_run_id()
    out = run_coevolution_economics(cfg, rid, generations=generations)
    typer.echo(f"Co-evolution economics written to {out}")


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
