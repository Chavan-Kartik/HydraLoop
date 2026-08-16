# HydraLoop

> "Every defence you deploy grows two new heads. Ship the defence that survives its own worst enemy."

HydraLoop is a synthetic, sandboxed, co-evolutionary adversarial payment security lab
for the era of **agentic commerce**.

## Why now

Autonomous agents are starting to make payments on people's behalf. That collapses the
human friction fraud used to trip over and turns the adversary into software that adapts at
machine speed. A defence validated on last year's static dataset is already stale. HydraLoop
is a wind tunnel for agentic-payment security: it *breeds* attacks and *hardens* defences
against them in a closed loop, then shows the attacker's return on investment collapse.

## Judges start here

- 3-minute walkthrough: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- One-pager: [docs/ONE_PAGER.md](docs/ONE_PAGER.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Responsible AI: [docs/RESPONSIBLE_AI.md](docs/RESPONSIBLE_AI.md)

## The thesis

Fraud is not a static dataset. It is an adaptive economic adversary. HydraLoop builds a
closed-loop environment where:

1. The **Red Team** generates constrained synthetic attack genomes.
2. The **Payment Digital Twin** simulates those attacks against synthetic legitimate traffic.
3. The **Blue Team** scores each transaction and selects a mitigation action.
4. Escaped attacks are mutated and fed back into the environment.
5. The Blue Team retrains and must pass a regression gauntlet before promotion.

Because the defence policy is live inside the twin, a step-up challenge actually reduces an
attacker's success probability in-simulation. The loop is a genuine adversarial environment,
not a retrain script.

## Safety and scope

- Synthetic data only; no real cardholder data or PII.
- No live payment systems targeted.
- No phishing content, deepfakes, persuasion scripts, or operational tooling generated.
- The Red Team's output space is a constrained Attack Genome DSL, never free-form text.

See [docs/RESPONSIBLE_AI.md](docs/RESPONSIBLE_AI.md) for the full safety and abstraction policy.

## Quickstart

Requires Python 3.11+ (3.12 recommended).

```bash
# One-time setup: dev deps + editable install.
make setup            # Linux / macOS / CI
.\make.ps1 setup      # Windows PowerShell

# End-to-end smoke run (manifest -> twin -> attacks -> baseline -> short loop).
make demo
.\make.ps1 demo

# Individual stages.
python -m hydraloop twin      # generate legitimate traffic
python -m hydraloop attack    # execute catalog genomes in the twin
python -m hydraloop train     # blue-team baseline + metrics
python -m hydraloop stack     # deep defence stack + ablation table
python -m hydraloop evolve    # red economics + quality-diversity search (Gate G4)
python -m hydraloop evaluate  # LOFO, zero-day, drift, fidelity, sensitivity tornado
python -m hydraloop loop      # co-evolution with the regression gauntlet
python -m hydraloop bench     # data-credibility benchmark: fidelity + TSTR/TRTS
python -m hydraloop bench --csv path/to/real.csv   # benchmark against a real dataset

# Command-center backend (serves REST + the arena WebSocket on :8000).
python -m hydraloop api

# Command-center UI in a second terminal (Next.js dev server on :3000).
cd ui && npm install && npm run dev
```

The UI renders from the live backend and falls back to a pre-seeded snapshot
under `ui/public/seed/` when the backend is unreachable, so it demos with the
venue wifi dead. Six screens: Arena (live loop), Threat Board (the abstracted
catalog), Attack Genome Lineage (mutation trail with plain-English briefs),
Investigation (SHAP reason codes plus counterfactual), Scoreboard (metrics),
and Governance (hash-chained audit trail with a live verify button). A "Judge
Demo Mode" button narrates the loop beat by beat.

Regenerate the offline seed snapshots after changing projections:

```bash
python scripts/seed_ui.py
```

### Docker

```bash
docker compose up --build
```

This runs the demo and writes artefacts (including `run_manifest.json`) into `reports/`.

### Tests

```bash
make test        # or: python -m pytest tests -v
make lint        # ruff + authenticity gate
```

## Layout

```
src/hydraloop/
  twin/         payment digital twin (discrete-event simulator)
  catalog/      threat-catalog loader
  red/          attack genome DSL, interpreter, economics, search
  blue/         feature bus, models, calibration, policy
  loop/         orchestrator, immune memory, regression gauntlet
  evaluation/   metrics, fidelity, generalisation, sensitivity
  api/          FastAPI + WebSocket command-center backend
catalog/attacks/  28 documented threat scenarios (YAML) across 7 families
configs/          seeds and experiment configs
ui/               Next.js command center
reports/runs/     per-run artefacts (git-ignored; exemplars in reports/examples/)
```

## Documents

- [docs/ONE_PAGER.md](docs/ONE_PAGER.md) - the pitch on one page
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - system diagram and data flow
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) - the 3-minute stage walkthrough
- [docs/SUBMISSION.md](docs/SUBMISSION.md) - the full write-up with results
- [docs/RESPONSIBLE_AI.md](docs/RESPONSIBLE_AI.md) - safety, abstraction policy, and governance
- [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) - assumptions register with sensitivity plans
- [docs/DATA_CARD.md](docs/DATA_CARD.md), [docs/MODEL_CARD.md](docs/MODEL_CARD.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- [docs/EDGE_CASES.md](docs/EDGE_CASES.md)
