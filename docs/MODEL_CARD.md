# HydraLoop Model Card

## Model Purpose

HydraLoop models are trained to detect and mitigate simulated payment fraud patterns inside a synthetic sandbox.

## Model Scope

- synthetic transactions,
- synthetic entities,
- synthetic behavioral sequences,
- simulated defense actions.

## Out of Scope

- production fraud detection,
- real-time payment authorization,
- regulatory compliance certification,
- live risk scoring of real users.

## Evaluation Metrics

- PR-AUC
- ROC-AUC
- recall at fixed FPR
- value detection rate
- expected calibration error
- friction rate
- review capacity usage
- attacker ROI reduction inside simulation

## Known Limitations

Performance is only valid within the simulated environment and documented assumptions.

## Human Oversight

Any future real-world use would require human review, governance, and authorized validation.