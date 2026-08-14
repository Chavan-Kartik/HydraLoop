# HydraLoop Limitations

HydraLoop is a prototype simulation environment.

## Main Limitations

1. Results are valid only inside the simulated environment.
2. Fidelity is measured against declared assumptions and internal baselines unless licensed external reference data is available.
3. The attacker model is a hypothesis, not an observation of real attackers.
4. The payment lifecycle is simplified and abstract.
5. The system does not model cryptography, network topology, tokenization, or issuer-specific logic.
6. Labels are simulated and may not represent real-world label delay or noise accurately.
7. LLM-assisted strategy generation, if used, is constrained by the attack DSL and cannot discover attacks outside the defined search space.
8. The system is not production-ready.

## What HydraLoop Does Not Claim

HydraLoop does not claim:

- real-world fraud detection performance,
- integration with any payment network,
- regulatory compliance,
- deployment readiness,
- superiority over production fraud systems.