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

Any assumption not listed here must be added before use.