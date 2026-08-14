# Edge-case register

Each row is an edge case that is designed for, not retrofitted. Where a test exists it is named.

## Twin

| Case | Handling | Test |
|---|---|---|
| Equal event timestamps | Deterministic tie-break via monotonic `sequence_no` in the clock | `test_clock.py::test_tiebreak_is_deterministic` |
| Capture without approved auth | Illegal transition raises | `test_lifecycle.py::test_capture_requires_approved_auth` |
| Chargeback without capture | Illegal transition raises | `test_lifecycle.py::test_chargeback_requires_capture` |
| Refund exceeds captured value | Rejected | `test_lifecycle.py::test_refund_cannot_exceed_capture` |
| Dispute past the dispute window | Dropped by rule | `test_labels.py::test_dispute_window_enforced` |
| Event past the simulation horizon | Marked `censored=True`, not discarded | `test_engine.py::test_horizon_censoring` |
| Step-up retry idempotency | Value counted once | `test_lifecycle.py::test_stepup_retry_idempotent` |
| Monetary amounts | Integer minor units throughout to avoid float drift | `test_schema.py::test_amounts_are_integer_minor_units` |
| Zero-transaction cardholder / zero-traffic merchant | Valid population members with empty histories | `test_population.py::test_inactive_entities_allowed` |

## Features

| Case | Handling | Test |
|---|---|---|
| Cold-start entity | `NULL` value plus explicit `*_is_new` flag, never silent zero-fill | `test_features.py::test_cold_start_flags` |
| Zero-variance z-score | Guarded, returns 0.0 not NaN | `test_features.py::test_zscore_zero_variance` |
| Left-censored rolling window at sim start | Carries a `window_coverage` value | `test_features.py::test_window_coverage` |
| Point-in-time correctness | Features only read events with timestamp <= as_of | `test_leakage.py::test_no_future_leakage` |

## Labels

| Case | Handling | Test |
|---|---|---|
| Unlabelled at training cutoff | Excluded or weighted, never a clean negative | `test_labels.py::test_unlabelled_excluded` |
| Friendly fraud | `disputed and not fraud` | `test_labels.py::test_friendly_fraud` |
| Unreported fraud | `fraud and not disputed` | `test_labels.py::test_unreported_fraud` |

## Policy

| Case | Handling | Test |
|---|---|---|
| Constraint infeasibility | Surfaced and relaxed in documented order | `test_operating_point.py::test_infeasible_relaxation` |
| Review-queue overflow | Spills to an auto-decision, logged | `test_policy.py::test_review_overflow` |
| Latency budget breach | Degraded mode: tabular-only fallback, logged | `test_serving.py::test_degraded_mode` |

## Red

| Case | Handling | Test |
|---|---|---|
| Unknown or out-of-range gene | Rejected at validation | `test_genome.py::test_out_of_range_rejected` |
| Canonical hash under key reordering | Stable | `test_genome.py::test_hash_stable_under_reorder` |
| Mutation past bounds | Clamped | `test_mutate.py::test_mutation_clamped` |
| Cross-family crossover | Rejected | `test_crossover.py::test_cross_family_rejected` |
| Budget exhaustion mid-episode | Episode aborts, partial cost recorded | `test_interpreter.py::test_budget_exhaustion` |

## Loop

| Case | Handling | Test |
|---|---|---|
| Gauntlet at generation 1 | Explicit bootstrap path, no incumbent required | `test_gauntlet.py::test_generation_one_bootstrap` |
| RNG stream separation | Red search and twin execution use distinct streams | `test_orchestrator.py::test_rng_streams_disjoint` |
| Ledger tamper | Hash-chain verified on load | `test_ledger.py::test_hash_chain_detects_tamper` |

## Determinism

| Case | Handling | Test |
|---|---|---|
| Golden-run reproducibility | Hash a canonical JSONL projection, not Parquet bytes (Parquet embeds writer metadata) | `test_determinism.py::test_golden_run_digest` |
