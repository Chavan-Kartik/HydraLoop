# HydraLoop

> "Every defence you deploy grows two new heads. Ship the defence that survives its own worst enemy."

HydraLoop is a synthetic, sandboxed, co-evolutionary adversarial payment security lab.

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

See [SAFETY.md](SAFETY.md) for the full abstraction policy.

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

# Command-center backend (serves REST + the arena WebSocket on :8000).
python -m hydraloop api

# Command-center UI in a second terminal (Next.js dev server on :3000).
cd ui && npm install && npm run dev
```

The UI renders from the live backend and falls back to a pre-seeded snapshot
under `ui/public/seed/` when the backend is unreachable, so it demos with the
venue wifi dead.

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
catalog/attacks/  24 documented threat scenarios (YAML)
configs/          seeds and experiment configs
ui/               Next.js command center
reports/runs/     per-run artefacts (git-ignored; exemplars in reports/examples/)
```

## Documents

- [SAFETY.md](SAFETY.md) - abstraction policy and scope containment
- [ASSUMPTIONS.md](ASSUMPTIONS.md) - assumptions register with sensitivity plans
- [DATA_CARD.md](DATA_CARD.md), [MODEL_CARD.md](MODEL_CARD.md)
- [LIMITATIONS.md](LIMITATIONS.md)
- [docs/EDGE_CASES.md](docs/EDGE_CASES.md)
