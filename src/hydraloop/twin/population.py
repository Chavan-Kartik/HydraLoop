"""Build a synthetic population of cardholders, merchants, devices, and payees.

Structural priors:
  - merchant popularity follows a Zipf law (a few merchants take most traffic);
  - device reuse is Pareto (most cardholders have one or two devices, a few many);
  - cardholder tenure is spread across the pre-simulation history.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .entities import Cardholder, Device, Merchant, Payee
from .rng import RngRegistry

# Synthetic merchant-category codes with per-category log-normal amount priors
# expressed in minor units. These are illustrative, not a real MCC table.
MCC_PRIORS: dict[int, tuple[float, float]] = {
    5411: (8.4, 0.6),   # grocery
    5812: (8.0, 0.7),   # eating places
    5541: (8.6, 0.5),   # fuel
    5999: (8.2, 0.9),   # misc retail
    4900: (9.0, 0.6),   # utilities
    6011: (10.2, 0.8),  # cash / transfer-like
    7995: (9.4, 1.1),   # high-variance category
    5732: (9.2, 0.8),   # electronics
}
MCC_LIST = list(MCC_PRIORS)
AGE_BANDS = ("18_24", "25_34", "35_44", "45_54", "55_plus")
SECONDS_PER_DAY = 86400.0


@dataclass
class Population:
    cardholders: list[Cardholder]
    merchants: list[Merchant]
    devices: dict[str, Device]
    payees: dict[str, Payee]
    merchant_weights: np.ndarray

    @property
    def n_cardholders(self) -> int:
        return len(self.cardholders)


def _zipf_weights(n: int, s: float = 1.1) -> np.ndarray:
    ranks = np.arange(1, n + 1, dtype=float)
    w = 1.0 / np.power(ranks, s)
    return w / w.sum()


def build_population(
    registry: RngRegistry,
    n_cardholders: int,
    n_merchants: int,
    history_days: float = 365.0,
) -> Population:
    r = registry.stream("population")

    merchants: list[Merchant] = []
    for i in range(n_merchants):
        mcc = MCC_LIST[i % len(MCC_LIST)]
        mu, sigma = MCC_PRIORS[mcc]
        onboarded = -float(r.uniform(0, history_days)) * SECONDS_PER_DAY
        merchants.append(
            Merchant(
                merchant_id=f"m{i:05d}",
                mcc=mcc,
                popularity_rank=i + 1,
                amount_mu_minor=mu,
                amount_sigma=sigma,
                onboarded_ts=onboarded,
            )
        )
    merchant_weights = _zipf_weights(n_merchants)

    cardholders: list[Cardholder] = []
    devices: dict[str, Device] = {}
    payees: dict[str, Payee] = {}

    for i in range(n_cardholders):
        cr = registry.stream(f"cardholder:{i}")
        created = -float(cr.uniform(0, history_days)) * SECONDS_PER_DAY
        # Pareto device count: most have 1-2 devices, a long tail has more.
        n_devices = int(min(8, 1 + cr.pareto(2.5)))
        device_ids = []
        for d in range(n_devices):
            did = f"d{i:05d}_{d}"
            devices[did] = Device(device_id=did, owner_id=f"c{i:05d}", created_ts=created)
            device_ids.append(did)
        n_payees = int(min(12, 1 + cr.pareto(1.8)))
        payee_ids = []
        for p in range(n_payees):
            pid = f"p{i:05d}_{p}"
            payees[pid] = Payee(payee_id=pid, owner_id=f"c{i:05d}", created_ts=created)
            payee_ids.append(pid)

        n_cats = int(cr.integers(2, 5))
        cats = list(cr.choice(MCC_LIST, size=n_cats, replace=False))
        raw = cr.dirichlet(np.ones(n_cats))
        mcc_weights = {int(c): float(w) for c, w in zip(cats, raw, strict=True)}

        balance = int(cr.lognormal(11.0, 0.8))
        limit = int(balance * float(cr.uniform(1.2, 3.0)))
        ch = cr.dirichlet(np.array([3.0, 1.0, 1.5]))
        cardholders.append(
            Cardholder(
                cardholder_id=f"c{i:05d}",
                created_ts=created,
                home_geo=int(cr.integers(0, 40)),
                age_band=AGE_BANDS[int(cr.integers(0, len(AGE_BANDS)))],
                balance_minor=balance,
                limit_minor=limit,
                activity_rate_per_day=float(cr.uniform(0.2, 3.0)),
                diurnal_peak_hour=float(cr.uniform(11.0, 20.0)),
                mcc_weights=mcc_weights,
                device_ids=device_ids,
                payee_ids=payee_ids,
                channel_weights={
                    "a2a": float(ch[0]),
                    "wallet": float(ch[1]),
                    "card_not_present": float(ch[2]),
                },
            )
        )

    return Population(
        cardholders=cardholders,
        merchants=merchants,
        devices=devices,
        payees=payees,
        merchant_weights=merchant_weights,
    )
