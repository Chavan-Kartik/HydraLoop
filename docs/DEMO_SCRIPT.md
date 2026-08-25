# Demo script (3 minutes)

Goal: land the agentic-commerce framing, show the loop working, and prove the results are
honest. Practise once so the timing is muscle memory. Everything runs offline from the seeded
snapshot, so the venue wifi cannot break the demo.

## Setup (before you present)

```bash
# Terminal 1: backend
python -m hydraloop api

# Terminal 2: UI
cd ui && npm run dev
```

Open `http://localhost:3000`. If the backend is down, the UI automatically shows the pre-seeded
snapshot and an "offline" badge; the demo still works.

## Beat 1 - the premise (30s)

On the **Arena** screen, click **JUDGE DEMO MODE**. Read the first caption aloud: autonomous
agents now initiate payments, so fraud becomes an adaptive, machine-speed adversary. Point at
the KPI bar: escape rate and attacker ROI are the two numbers that matter, and both should fall.

## Beat 2 - the loop runs (45s)

Let demo mode advance, or press **RUN CO-EVOLUTION** for a live run. Narrate: the red team
escapes through specific modes (call them out from the ticker), the blue team retrains from
immune memory, and the **regression gauntlet** blocks a model that would have regressed. That
rollback is the point: we never ship a weaker defence.

## Beat 3 - the attack, in plain English (30s)

Open **Threat Board**, filter to **Agentic Commerce**. These four scenarios model
agent-initiated fraud: mandate drift, checkout takeover, agent-swarm probing, destination
redirection - all behavioural-metadata-only, no recipes. Open **Lineage**, click a node, and
read the one-paragraph brief so judges see the attack described in words, not just genes.

## Beat 4 - the defence is explainable (20s)

Open **Investigation**. Pick a flagged transaction. Show the SHAP reason codes and the
counterfactual: "if the payee were not new, risk drops by N points." This is what an analyst
would act on.

## Beat 5 - it is honest (25s)

Open **Governance**. The run history is a hash chain. Click **Verify chain**: green. Say that
any edit to history would break the chain on the next verification. Then mention the data
credibility benchmark (`python -m hydraloop bench`) that reports discriminator AUC and TSTR /
TRTS against a shifted or real reference, so we measure fidelity instead of asserting it.

## Beat 6 - the takeaway (10s)

Return to the KPI bar. Escape rate down, attacker ROI collapsing, every decision on a
tamper-evident trail. Close with the line: we do not just detect fraud, we make the attack
uneconomic - and we can prove it.

## If asked "is this real data?"

No, and deliberately so. It is fully synthetic, which is why anyone can run it with no PII, no
credentials, and no NDA. When a real dataset is available, `python -m hydraloop bench --csv
path/to/real.csv` normalises it and reports how close the synthetic traffic is and how well the
detector transfers.
