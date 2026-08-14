"""Online per-entity state and the point-in-time feature snapshot.

The feature bus runs inside the twin at AUTH_REQUEST time and freezes its output
into the transaction record. Because a feature can only read the state that
exists at ``as_of``, future information cannot leak into training data by
construction, not merely by a downstream test.

Cold-start entities get ``None`` plus an explicit ``*_is_new`` flag rather than a
silent zero, so a model can tell "no history" apart from "a value of zero".
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .entities import Cardholder
from .schema import AuthRequest, Channel

_H1 = 3600.0
_H24 = 86400.0
_D7 = 604800.0

_CHANNEL_CODE = {Channel.A2A: 0, Channel.WALLET: 1, Channel.CARD_NOT_PRESENT: 2}

FEATURE_COLUMNS = [
    "account_age_days",
    "account_is_new",
    "txn_count_lifetime",
    "velocity_1h",
    "velocity_24h",
    "velocity_7d",
    "amount_minor",
    "amount_log",
    "amount_zscore",
    "amount_z_is_new",
    "balance_ratio",
    "device_is_new",
    "payee_is_new",
    "hour_of_day",
    "day_of_week",
    "channel_code",
    "mcc",
    "window_coverage_7d",
]


@dataclass
class EntityState:
    created_ts: float
    txn_count: int = 0
    amount_sum: float = 0.0
    amount_sqsum: float = 0.0
    recent_ts: deque[float] = field(default_factory=deque)
    devices_seen: set[str] = field(default_factory=set)
    payees_seen: set[str] = field(default_factory=set)

    def _trim(self, as_of: float) -> None:
        cutoff = as_of - _D7
        while self.recent_ts and self.recent_ts[0] < cutoff:
            self.recent_ts.popleft()

    def velocities(self, as_of: float) -> tuple[int, int, int]:
        self._trim(as_of)
        v1 = v24 = v7 = 0
        for t in self.recent_ts:
            age = as_of - t
            if age <= _H1:
                v1 += 1
            if age <= _H24:
                v24 += 1
            if age <= _D7:
                v7 += 1
        return v1, v24, v7

    def amount_zscore(self, amount: float) -> float | None:
        n = self.txn_count
        if n < 2:
            return None
        mean = self.amount_sum / n
        var = max(0.0, self.amount_sqsum / n - mean * mean)
        if var <= 1e-9:  # zero-variance guard: constant history has no z-score
            return 0.0
        return (amount - mean) / (var**0.5)

    def observe(self, ts: float, amount: float, device_id: str, payee_id: str | None) -> None:
        self.txn_count += 1
        self.amount_sum += amount
        self.amount_sqsum += amount * amount
        self.recent_ts.append(ts)
        self.devices_seen.add(device_id)
        if payee_id is not None:
            self.payees_seen.add(payee_id)


def snapshot_features(
    state: EntityState,
    holder: Cardholder,
    ar: AuthRequest,
    as_of: float,
) -> dict[str, float | None]:
    v1, v24, v7 = state.velocities(as_of)
    amount = float(ar.amount_minor)
    z = state.amount_zscore(amount)
    age_days = max(0.0, (as_of - state.created_ts) / _D7 * 7.0)
    hour = (as_of / 3600.0) % 24.0
    dow = int((as_of // _H24) % 7)
    balance_ratio = amount / holder.balance_minor if holder.balance_minor > 0 else None
    window_cov = min(1.0, (as_of - state.created_ts) / _D7) if as_of > state.created_ts else 0.0
    return {
        "account_age_days": age_days,
        "account_is_new": 1.0 if state.txn_count == 0 else 0.0,
        "txn_count_lifetime": float(state.txn_count),
        "velocity_1h": float(v1),
        "velocity_24h": float(v24),
        "velocity_7d": float(v7),
        "amount_minor": amount,
        "amount_log": math.log1p(max(0.0, amount)),
        "amount_zscore": z,
        "amount_z_is_new": 1.0 if z is None else 0.0,
        "balance_ratio": balance_ratio,
        "device_is_new": 1.0 if ar.device_id not in state.devices_seen else 0.0,
        "payee_is_new": 1.0
        if (ar.payee_id is not None and ar.payee_id not in state.payees_seen)
        else 0.0,
        "hour_of_day": hour,
        "day_of_week": float(dow),
        "channel_code": float(_CHANNEL_CODE[ar.channel]),
        "mcc": float(ar.mcc),
        "window_coverage_7d": float(window_cov),
    }
