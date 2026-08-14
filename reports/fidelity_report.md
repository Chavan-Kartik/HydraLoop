# Fidelity report (v0)

- transactions: 150
- fraud rate (ground truth): 0.0000
- dispute rate: 0.0000
- correlation-structure Frobenius norm (off-diagonal): 0.519

## Lifecycle validity (must be zero)
- captured_without_approval: 0
- disputed_without_capture: 0

## Marginal summaries

| feature | mean | std | p05 | p50 | p95 |
|---|---:|---:|---:|---:|---:|
| amount_minor | 7528.56 | 9195.95 | 1481.60 | 5021.50 | 20022.05 |
| velocity_24h | 0.59 | 0.81 | 0.00 | 0.00 | 2.00 |
| hour_of_day | 13.49 | 5.61 | 2.54 | 13.45 | 22.10 |
| day_of_week | 1.21 | 0.96 | 0.00 | 1.00 | 3.00 |
| account_age_days | 184.81 | 111.68 | 26.77 | 180.32 | 344.41 |

## Plots
![fidelity_amount_hist.png](fidelity_amount_hist.png)
![fidelity_hour_hist.png](fidelity_hour_hist.png)
