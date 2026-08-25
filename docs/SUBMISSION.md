# HydraLoop - submission summary

The formal walkthrough required by the challenge is **[SUBMISSION.docx](SUBMISSION.docx)**.
That file is generated, not written: `scripts/build_submission_docx.py` reads the JSON
artifacts a run produces and refuses to build if one is missing, so no figure in it can
drift away from what the code actually measured. This page is the short version.

## What it is

A sandboxed lab where an attacker and a defender improve against each other. The red team
encodes payment fraud as constrained, machine-readable attack genomes and searches for the
variants that pay. A payment digital twin runs them against synthetic legitimate traffic
through a full transaction lifecycle. The blue team scores every transaction at decision
time, and whatever escapes feeds back so the detector retrains and has to clear a
regression gauntlet before it can be promoted.

All data is synthetic. Ground-truth fraud labels exist only inside the simulator and are
never model inputs.

## Headline numbers

Measured on the temporal test split of one reproducible run: 60,000 legitimate sessions
over a 120-day horizon, seed 42, config `configs/submission.yaml`. Test holds 9,279
transactions of which 261 are fraudulent. Training only sees earlier transactions, and
only disputes that have already matured.

| Metric | Gradient-boosted model | Velocity rule |
|---|---:|---:|
| PR-AUC | 0.9587 | 0.2120 |
| ROC-AUC | 0.9963 | 0.8852 |
| Recall at 1% FPR | 0.9425 | 0.2184 |
| Share of fraud value stopped | 0.9719 | 0.1968 |
| F1 at the operating point | 0.824 | 0.279 |
| Realised FPR | 0.00998 | 0.00998 |

Confusion matrix at that point: 246 true positives, 90 false positives, 15 false
negatives, 8,928 true negatives.

**Precision is quoted twice on purpose.** It is the one headline metric that moves with
the fraud base rate, and the simulator deliberately runs a richer fraud mix than a real
portfolio so there are enough positives to measure. At the test set's own 2.8% prevalence
precision is 0.732; restated at a realistic 0.5% base rate, holding recall and FPR fixed,
it is 0.322. The second number is the one a fraud-operations team would plan capacity
against. Recall and FPR do not depend on prevalence, which is why they carry the headline.

## Per-model contribution

| Model | PR-AUC | Recall at 1% FPR |
|---|---:|---:|
| Tabular (LightGBM) | 0.9598 | 0.9425 |
| Sequence (GRU) | 0.5860 | 0.5939 |
| Narrative | 0.6472 | 0.5517 |
| Sentinel (legit-only) | 0.6451 | 0.6169 |
| Graph (GraphSAGE) | 0.0386 | 0.0000 |
| Ensemble | 0.9598 | 0.9425 |

Two things worth stating rather than leaving to be discovered. The gradient-boosted model
on the point-in-time feature bus does nearly all the work, and the graph model contributes
nothing on this configuration; it is a candidate for removal, not a strength. The ensemble
row equals the tabular row because the combiner correctly selected that one model, so the
ensemble is currently acting as a selector rather than a genuine blend.

The sentinel earns its place elsewhere: trained only on legitimate traffic, it recovers
0.502 recall at 1% FPR on held-out attack families no supervised component has seen.

## Fidelity, and what it does not prove

Against an independent draw from the same generator, a discriminator scores AUC 0.5006
over 18 shared features, and transfer runs at 0.808 recall training on synthetic and
testing on the reference, 0.766 in reverse.

That reference is synthetic. **No licensed external dataset is bundled here, so these
numbers show the simulator is stationary and reproducible, not that it resembles real
payment data, and we do not claim otherwise.** The harness that would measure realism is
built and tested: `hydraloop bench --csv <file>` or `--preset sparkov|paysim` normalises an
external transaction file into the same feature space and reports the same discriminator
and TSTR/TRTS figures against it. Pointing it at real data is the highest-value validation
step remaining, and it needs a dataset licence rather than more code.

## Known limits

- Fidelity against real payment data is unproven, as above.
- Attacks generated from a bounded genome are more regular than real fraud. A ROC-AUC near
  0.99 means the model learns the generator; it is not a forecast of live performance.
- Single runs, no repeated seeds or confidence intervals. The config is pinned and the
  commands below reproduce everything, but no error bars are claimed.
- Twelve of the 28 catalog scenarios are documented but not yet simulatable, and are
  marked as such rather than counted toward simulation coverage.
- Zero-day recall from the supervised stack alone is weak, which is why the sentinel is in
  the ensemble. The leave-one-family-out matrix reports its weak cells rather than hiding
  them.

## Reproducing this

```bash
pip install -r requirements.txt
pytest -q
python scripts/canonical_eval.py
python -m hydraloop stack --config configs/submission.yaml --run-id run_sub_stack
python -m hydraloop bench --config configs/submission.yaml --run-id run_bench
python scripts/build_submission_docx.py
```

`reports/runs/` is gitignored, so the artifacts these commands write are also committed
under [`reports/examples/example_submission/`](../reports/examples/example_submission) for
inspection without a re-run.

For the prototype: `python -m hydraloop api`, then `cd ui && npm install && npm run dev`.
