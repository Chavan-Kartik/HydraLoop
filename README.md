# HydraLoop

> **“Every defence you deploy grows two new heads. Ship the defence that survives its own worst enemy.”**

HydraLoop is a synthetic, sandboxed, co-evolutionary adversarial payment security lab built for the Mastercard Innovation Challenge 2026.

## The Thesis
Fraud is not a static dataset. It is an adaptive economic adversary. 

HydraLoop builds a closed-loop environment where:
1. The **Red Team** generates constrained synthetic attack genomes.
2. The **Payment Digital Twin** simulates those attacks against synthetic legitimate traffic.
3. The **Blue Team** scores transactions and selects mitigation actions.
4. Escaped attacks are mutated and fed back into the environment.
5. The Blue Team retrains and must pass a regression gauntlet before promotion.

## Safety & Scope
This project is a research prototype.
- Synthetic data only
- No real cardholder data or PII
- No live payment systems targeted
- No phishing content, deepfakes, or operational tooling generated

All attack scenarios are represented as behavioral parameters inside a constrained simulation environment.

## Quickstart
```bash
make setup
make test
make demo