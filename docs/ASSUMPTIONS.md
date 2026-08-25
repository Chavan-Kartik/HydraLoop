# HydraLoop Assumptions Register

Every assumed parameter must be tracked here.

| ID | Assumption | Value / Range | Justification | Validation Status | Sensitivity Plan |
|---|---|---:|---|---|---|
| A01 | Simulated fraud base rate | 0.1% to 1.5% | configurable imbalance for payment-like settings | assumed | sweep low/high |
| A02 | Step-up challenges increase attacker abandonment | configurable probability | friction affects adversary success | assumed | sweep abandon probability |
| A03 | Some fraud labels arrive late via disputes | mean delay configurable | disputes can be delayed | assumed | sweep delay distribution |
| A04 | Friendly fraud exists among disputes | configurable rate | not all disputes are true fraud | assumed | sweep noise rate |
| A05 | Mule networks show fan-out/fan-in behavior | graph feature hypothesis | common analytical pattern | assumed | graph feature ablation |
| A06 | Customer friction budget is operationally limited | example: 2% step-up | businesses constrain user friction | assumed | policy budget sweep |
| A07 | Review capacity is limited | example: 400 reviews/day | operational teams have capacity limits | assumed | sweep capacity |
| A08 | Amount distributions are log-normal per merchant category | configurable | common transaction modeling assumption | assumed | distribution sensitivity |
| A09 | Legitimate user arrivals have diurnal and weekly patterns | configurable | human activity is periodic | assumed | temporal sensitivity |
| A10 | GenAI may scale attacks, but HydraLoop simulates only behavioral footprints | abstraction policy | safety constraint | design decision | not applicable |

## Cost model (Phase 5 decision policy)

These feed `blue/costs.py`. Every entry is swept +/-50% in the sensitivity analysis.

| ID | Parameter | Value | Range | Justification | Sensitivity Plan |
|---|---|---:|---|---|---|
| C01 | loss_given_fraud | 1.0 | 0.5 - 1.0 | settled fraud loses close to full value | sweep |
| C02 | false_positive_value_frac | 0.15 | 0.05 - 0.30 | blocking a good customer loses goodwill and value | sweep |
| C03 | friction_frac (step-up) | 0.010 | 0.002 - 0.03 | step-up friction as a fraction of value | sweep |
| C04 | legit_abandon_prob | 0.04 | 0.01 - 0.10 | good customers occasionally abandon at step-up | sweep |
| C05 | hold_frac | 0.015 | 0.005 - 0.04 | delaying a payment carries a cost | sweep |
| C06 | review_cost_minor | 300 | 100 - 800 | fixed operational cost of a manual review | sweep |
| C07 | soft_warn_frac | 0.002 | 0.0005 - 0.01 | soft-warn is cheap friction | sweep |
| C08 | block_prob_step_up | 0.60 | 0.4 - 0.8 | fraction of fraud blocked by a step-up | sweep |
| C09 | block_prob_soft_warn | 0.20 | 0.1 - 0.4 | soft-warn deters some fraud | sweep |
| C10 | block_prob_hold | 0.50 | 0.3 - 0.7 | a hold deters fraud during review | sweep |
| C11 | block_prob_manual_review | 0.85 | 0.6 - 0.95 | reviewers block most true fraud | sweep |

## Attacker economics (Phase 9 fitness and resource costs)

Fitness = w_value*value_settled - w_resource*resource_cost - w_time*time_to_cashout
- w_detection*detection_events - w_friction*friction_events, with a hard guard that
a zero-attempt genome scores minus infinity (no degenerate never-transact optimum).
Every weight and unit cost is swept +/-50% in the sensitivity analysis.

| ID | Parameter | Value | Range | Justification | Sensitivity Plan |
|---|---|---:|---|---|---|
| E01 | w_value | 1.0 | fixed reference | value settled is the numeraire | anchor |
| E02 | w_resource | 1.0 | 0.5 - 1.5 | resources priced in the same minor units | sweep |
| E03 | w_time | 200 | 100 - 300 | cost per hour to cash out | sweep |
| E04 | w_detection | 30000 | 15000 - 45000 | a detection event is expensive for the attacker | sweep |
| E05 | w_friction | 8000 | 4000 - 12000 | each step-up encountered costs the attacker | sweep |
| E06 | cost_mule_account | 5000 | 2500 - 7500 | price of a mule account | sweep |
| E07 | cost_synthetic_identity | 8000 | 4000 - 12000 | price of a synthetic identity | sweep |
| E08 | cost_device | 1500 | 750 - 2250 | price of a burner device | sweep |
| E09 | cost_operator_hour | 4000 | 2000 - 6000 | attacker operator hourly cost | sweep |

Any assumption not listed here must be added before use.