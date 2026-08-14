"""Session arrivals as a non-homogeneous Poisson process.

Each cardholder generates sessions at a base rate modulated by a diurnal curve
(peaking at their personal peak hour) and a weekly curve (quieter at weekends).
Arrivals are produced by thinning: propose at the per-cardholder maximum rate,
accept with probability equal to the modulation at the proposed instant.
"""

from __future__ import annotations

import numpy as np

from .entities import Cardholder
from .population import SECONDS_PER_DAY
from .rng import RngRegistry

_WEEKLY = np.array([1.0, 1.0, 1.0, 1.05, 1.15, 0.85, 0.7])  # Mon..Sun


def _diurnal(hour: float, peak: float) -> float:
    # Wrapped Gaussian bump on a 24h clock, floored so nights are quiet not dead.
    d = min(abs(hour - peak), 24.0 - abs(hour - peak))
    return 0.15 + 0.85 * float(np.exp(-(d**2) / (2 * 3.0**2)))


def _modulation(ts: float, peak_hour: float) -> float:
    hour = (ts / 3600.0) % 24.0
    dow = int((ts // SECONDS_PER_DAY) % 7)
    return _diurnal(hour, peak_hour) * _WEEKLY[dow]


def cardholder_arrivals(
    holder: Cardholder, gen: np.random.Generator, horizon_s: float
) -> list[float]:
    rate_per_s = holder.activity_rate_per_day / SECONDS_PER_DAY
    lam_max = rate_per_s * 1.0  # modulation peak is <= 1.0
    if lam_max <= 0:
        return []
    out: list[float] = []
    t = 0.0
    while True:
        t += float(gen.exponential(1.0 / lam_max))
        if t >= horizon_s:
            break
        if gen.random() < _modulation(t, holder.diurnal_peak_hour):
            out.append(t)
    return out


def population_arrivals(
    registry: RngRegistry, cardholders: list[Cardholder], horizon_s: float
) -> list[tuple[float, str]]:
    arrivals: list[tuple[float, str]] = []
    for i, holder in enumerate(cardholders):
        gen = registry.stream(f"arrivals:{i}")
        for ts in cardholder_arrivals(holder, gen, horizon_s):
            arrivals.append((ts, holder.cardholder_id))
    arrivals.sort()
    return arrivals
