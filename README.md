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

- 3-minute walkthrough: [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md)
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

## The generative red team

Two places can be driven by a language model: the strategist that proposes the
next genome inside the co-evolution loop, and the Identify step that turns a
plain-English threat description into a simulatable attack.

Neither ever asks a model for attack content. The prompt requests bounded
numeric parameters and behavioural signal names as JSON, and the reply passes
three tiers before it can reach the twin:

1. **Strict** - a complete, valid genome is accepted verbatim.
2. **Repair** - a partial or out-of-bounds proposal is merged onto the parent,
   clamped to the DSL's hard bounds, then validated.
3. **Refuse** - anything still invalid is logged as a refusal and the
   deterministic planner runs instead.

The Attack Genome DSL is the guardrail. A model can strengthen the search; it
cannot push an out-of-policy attack through.

**It is off by default.** Unconfigured, the lab uses a deterministic planner and
a keyword mapper, so everything runs offline with no API key and no network. To
enable a model:

```bash
HYDRALOOP_LLM_PROVIDER=openai     # or: ollama, none (default)
HYDRALOOP_LLM_BASE_URL=https://api.groq.com/openai/v1
HYDRALOOP_LLM_MODEL=llama-3.3-70b-versatile
HYDRALOOP_LLM_API_KEY=...
HYDRALOOP_LLM_TIMEOUT=10          # seconds, optional
```

`openai` speaks to any OpenAI-compatible `/chat/completions` host; `ollama`
targets a local server. `/api/health` reports whether a model is configured, and
the Lab's Identify step names which mapper produced each result, so it is always
visible which path ran. A provider that stops answering trips a breaker after
three consecutive failures and the run falls back rather than stalling.

## Safety and scope

- Synthetic data only; no real cardholder data or PII.
- No live payment systems targeted.
- No phishing content, deepfakes, persuasion scripts, or operational tooling generated.
- The Red Team's output space is a constrained Attack Genome DSL, never free-form text.

See [docs/RESPONSIBLE_AI.md](docs/RESPONSIBLE_AI.md) for the full safety and abstraction policy.

## Quickstart

Requires Python 3.11+ (3.12 recommended), and Node 18.17+ for the UI.

```bash
# One-time setup: dev deps + editable install.
make setup            # Linux / macOS / CI
.\make.ps1 setup      # Windows PowerShell

# Or without a task runner. requirements.txt is the pinned lock that reproduces
# the reported numbers; pyproject.toml is the loose declaration.
pip install -r requirements.txt && pip install -e .
pip install -e ".[dev]"    # unpinned alternative

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
venue wifi dead. Seven screens:

| Screen | What it shows |
|---|---|
| Lab (`/`) | Type any threat description and watch Identify to Detect run step by step |
| Arena | Recorded multi-generation co-evolution replay |
| Threats | The abstracted catalog of 28 scenarios; each card runs in the Lab |
| Lineage | Genome mutation trail with plain-English briefs |
| Cases | SHAP reason codes plus a counterfactual for the latest episode |
| Metrics | Escape rate and archive recall by generation |
| Audit | Hash-chained ledger with a live verify button |

Regenerate the offline seed snapshots after changing projections:

```bash
python scripts/seed_ui.py
```

### Docker

```bash
docker compose up --build          # backend on http://localhost:8000
```

The image serves the API, which is what the UI needs. It omits torch, because the
only component that imports it is the defence-stack sequence model, reachable
through the `stack` and `evaluate` commands rather than any API route. To run a
CLI stage in the container instead:

```bash
docker compose run --rm api python -m hydraloop demo
```

The same image deploys unchanged to any container host. It listens on `$PORT`,
which managed platforms inject for you, and falls back to 7860 when nothing sets
it. Set `HYDRALOOP_ALLOWED_ORIGINS` to a comma-separated list of front-end
origins; `*.vercel.app` is already permitted.

### Tests

```bash
make test        # or: python -m pytest tests -v
make lint        # ruff
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
- [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) - a self-guided 3-minute tour of the running app
- [docs/SUBMISSION.md](docs/SUBMISSION.md) - the full write-up with results
- [docs/RESPONSIBLE_AI.md](docs/RESPONSIBLE_AI.md) - safety, abstraction policy, and governance
- [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) - assumptions register with sensitivity plans
- [docs/DATA_CARD.md](docs/DATA_CARD.md), [docs/MODEL_CARD.md](docs/MODEL_CARD.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- [docs/EDGE_CASES.md](docs/EDGE_CASES.md)
