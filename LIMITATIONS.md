# Limitations

HydraLoop is a synthetic, sandboxed research lab. Its results describe behaviour
inside its own digital twin, not any production payment network. The specific
limitations below are stated plainly so no result is over-claimed.

1. **Fidelity is against declared priors, not proprietary ground truth.** No
   real transaction data is used, and no permissive external reference dataset is
   bundled (obtaining one may require credentials we do not acquire without
   asking). The fidelity story therefore rests on declared-prior agreement,
   structural-validity checks, and the sensitivity analysis. The discriminator-AUC
   check runs only when a reference is supplied; otherwise it is reported as
   unavailable rather than faked.

2. **The sentinel's zero-day recall is weak.** The Isolation Forest trained on
   legitimate traffic only frequently scores near-zero recall on the sealed
   zero-day holdout at a 1% FPR. Anomaly detection on these behavioural features
   does not reliably separate novel fraud from the tail of normal behaviour; we
   report this number honestly rather than tuning it to look good.

3. **Cross-population transfer is approximate.** Each generation rebuilds the twin
   with a fresh population, so a detector trained on one generation is evaluated
   against different entities. Transfer relies on behavioural features
   generalising; the LOFO matrix exposes families where this transfer is weak.

4. **Small-data instability in the ensemble and calibration.** With modest
   generation sizes, the stacked meta-learner overfits tiny validation folds, so
   the ensemble selects its combiner on out-of-fold predictions and can fall back
   to a single base model. ECE is likewise sensitive to sample size and binning;
   we report both equal-width and equal-mass ECE.

5. **The graph model uses unparameterised mean-pool aggregation.** GraphSAGE
   embeddings are structural (type and multi-hop degree signatures) with a learned
   logistic head, not end-to-end trained message passing. This is a deliberate
   stability trade-off and limits the relational patterns the graph layer can
   express.

6. **Abstraction ceiling by design.** Attacks are modelled at the behavioural-
   footprint level only. HydraLoop contains no operational attack tooling and no
   generated deceptive content, so it cannot and does not evaluate content-level
   detection. Any claim about real-world social-engineering text is out of scope.

7. **The LLM strategist is optional and offline by default.** The demo path uses a
   deterministic template planner; when an external model is injected, only
   schema-valid genome JSON is accepted and every refusal is logged. Results do
   not depend on any model or network being available.

8. **Economic weights are assumptions, not measurements.** The attacker fitness
   weights and resource unit costs in `ASSUMPTIONS.md` are plausible placeholders
   swept +/-50% in the tornado analysis; absolute ROI figures are illustrative and
   only the direction (collapse under a hardening policy) is claimed.
