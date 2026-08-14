"""Delayed, noisy labels.

Two real-world facts almost no hackathon models, both handled here:
  - friendly fraud: a legitimate transaction that gets disputed (observed as
    fraud, but ``is_fraud`` is false);
  - under-reported fraud: genuine fraud that is never disputed (observed as
    legitimate, but ``is_fraud`` is true).

Disputes also arrive late, so a transaction's observed label can flip after the
training cutoff. Rows that are still unlabelled at the cutoff must be excluded or
weighted, never treated as clean negatives.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .population import SECONDS_PER_DAY


@dataclass(frozen=True)
class LabelOutcome:
    is_fraud: bool  # ground truth
    disputed: bool
    dispute_ts: float | None
    charged_back: bool


class LabelModel:
    def __init__(
        self,
        delay_hours_mean: float,
        delay_hours_std: float,
        friendly_fraud_rate: float,
        under_report_rate: float,
        dispute_window_days: int,
    ) -> None:
        self.delay_hours_mean = delay_hours_mean
        self.delay_hours_std = max(1e-3, delay_hours_std)
        self.friendly_fraud_rate = friendly_fraud_rate
        self.under_report_rate = under_report_rate
        self.dispute_window_s = dispute_window_days * SECONDS_PER_DAY

    def _delay_s(self, gen: np.random.Generator) -> float:
        # Log-normal so that most disputes are prompt with a long tail.
        sigma = 0.6
        mu = np.log(max(1.0, self.delay_hours_mean)) - 0.5 * sigma**2
        hours = float(gen.lognormal(mu, sigma))
        return hours * 3600.0

    def resolve(
        self,
        is_fraud: bool,
        captured: bool,
        settlement_ts: float,
        gen: np.random.Generator,
    ) -> LabelOutcome:
        if not captured:
            return LabelOutcome(is_fraud=is_fraud, disputed=False, dispute_ts=None, charged_back=False)

        if is_fraud:
            disputed = gen.random() >= self.under_report_rate
        else:
            disputed = gen.random() < self.friendly_fraud_rate

        if not disputed:
            return LabelOutcome(is_fraud=is_fraud, disputed=False, dispute_ts=None, charged_back=False)

        delay = self._delay_s(gen)
        if delay > self.dispute_window_s:
            # Past the dispute window: the dispute right lapses, so no label.
            return LabelOutcome(is_fraud=is_fraud, disputed=False, dispute_ts=None, charged_back=False)

        dispute_ts = settlement_ts + delay
        # A disputed transaction is charged back unless represented successfully.
        charged_back = gen.random() < 0.85
        return LabelOutcome(
            is_fraud=is_fraud,
            disputed=True,
            dispute_ts=dispute_ts,
            charged_back=charged_back,
        )
