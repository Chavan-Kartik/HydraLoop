# HydraLoop - one page

## The problem

Autonomous agents are beginning to transact on people's behalf. This removes the human
friction that fraud used to stumble over and turns the adversary into software that adapts at
machine speed. Fraud defences are validated on static historical datasets, so they are stale
the moment an attacker changes behaviour. There is no safe, shared place to ask "what happens
when the attacker adapts faster than we retrain?"

## The idea

HydraLoop is a synthetic, sandboxed, co-evolutionary lab: a wind tunnel for agentic-payment
security. It has three parts locked in a closed loop.

1. A **payment digital twin** simulates legitimate traffic and executes attacks against a live
   defence policy, so a step-up challenge really does lower an attacker's success in-simulation.
2. A **red team** encodes attacks as a constrained genome (never free text), then uses
   quality-diversity search and an economic fitness function to evolve the ones that pay.
3. A **blue team** scores every transaction with a calibrated ensemble and picks a
   cost-sensitive action; a regression gauntlet must pass before any new model is promoted.

## Why it is a game-changer

- **On-theme for agentic commerce.** A dedicated agent-initiated fraud family models machine-
  speed cadence, delegated-mandate drift, and agent-swarm probing.
- **It measures the attacker, not just the model.** The headline result is attacker ROI
  collapsing toward zero as the loop hardens, not a single AUC number.
- **It is honest by construction.** A hash-chained ledger makes the run tamper-evident, and a
  data-credibility benchmark reports discriminator AUC and TSTR/TRTS against a shifted or real
  reference instead of asserting realism.
- **It is safe to run anywhere.** Fully synthetic, no PII, no live systems, no attack recipes.

## What you can see in three minutes

Lab (type any threat description and watch Identify to Detect run step by step),
Arena (the loop running live), Threats (28 abstracted scenarios across 7 families),
Lineage (the mutation trail with plain-English briefs), Cases (SHAP reason codes plus a
counterfactual), Metrics (escape rate and recall by generation), and Audit
(verify the hash chain yourself).

## Results to point at

- Escape rate falls generation over generation while the friction budget is respected.
- Attacker ROI collapses and behavioural coverage of the search space climbs.
- The gauntlet blocks regressive models (visible rollbacks), and the audit chain verifies.
