"""Entity agents and their behavioural priors.

A cardholder is defined by *normality*: a home geography, a merchant-category
mix, an amount distribution, an activity rhythm, and a known device and payee
set. Fraud later shows up precisely as deviation from these priors, which is why
legitimate traffic has to be defined before any attack exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Merchant:
    merchant_id: str
    mcc: int
    popularity_rank: int
    amount_mu_minor: float  # log-normal mu on minor units
    amount_sigma: float
    onboarded_ts: float


@dataclass
class Device:
    device_id: str
    owner_id: str
    created_ts: float


@dataclass
class Payee:
    payee_id: str
    owner_id: str
    created_ts: float


@dataclass
class Cardholder:
    cardholder_id: str
    created_ts: float
    home_geo: int
    age_band: str
    balance_minor: int
    limit_minor: int
    activity_rate_per_day: float
    diurnal_peak_hour: float
    mcc_weights: dict[int, float]
    device_ids: list[str] = field(default_factory=list)
    payee_ids: list[str] = field(default_factory=list)
    channel_weights: dict[str, float] = field(default_factory=dict)
