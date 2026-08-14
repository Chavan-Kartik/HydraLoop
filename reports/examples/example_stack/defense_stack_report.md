# Defence stack ablation

- run: example_stack

| model | PR-AUC (obs) | recall@1%FPR (obs) | PR-AUC (true) | recall@1%FPR (true) |
|---|---:|---:|---:|---:|
| tabular | 0.4027 | 0.16 | 0.4851 | 0.1515 |
| sequence | 0.5658 | 0.2 | 0.763 | 0.4242 |
| graph | 0.31 | 0.2 | 0.4431 | 0.1818 |
| narrative | 0.4167 | 0.08 | 0.5689 | 0.0909 |
| sentinel | 0.4153 | 0.0 | 0.5697 | 0.0 |
| ensemble | 0.5197 | 0.08 | 0.7241 | 0.1818 |

Isolation Forest sentinel solo recall on the sealed zero-day holdout @1% FPR: 0.0
