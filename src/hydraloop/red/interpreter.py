"""Interpret a genome into concrete fraud sessions inside the twin.

The interpreter is deliberately dumb in Phase 3: no optimisation, no evolution,
just faithful execution of the genes as a fraud operator would drive them.
Budget exhaustion aborts the episode and leaves the partial cost recorded.
"""

from __future__ import annotations

import numpy as np

from ..twin.engine import SessionSpec
from ..twin.entities import Cardholder
from ..twin.schema import Channel
from .dsl.genome import Genome
from .ledger import BudgetExhausted, ResourceLedger

_CHANNELS = {"a2a": Channel.A2A, "wallet": Channel.WALLET, "card_not_present": Channel.CARD_NOT_PRESENT}
_OP_HOURS_PER_TXN = 0.1


def _pick_channel(weights: dict[str, float], gen: np.random.Generator) -> Channel:
    names = list(weights)
    w = np.array([max(0.0, weights[n]) for n in names], dtype=float)
    if w.sum() <= 0:
        w = np.ones(len(names))
    w = w / w.sum()
    return _CHANNELS[names[int(gen.choice(len(names), p=w))]]


def interpret_episode(
    genome: Genome,
    holder: Cardholder,
    start_ts: float,
    gen: np.random.Generator,
    ledger: ResourceLedger,
    episode_id: str,
) -> list[SessionSpec]:
    g = genome.genes
    budget = g["resource_budget"]
    amt = g["amount_policy"]
    timing = g["timing_policy"]
    device_policy = g["device_policy"]
    fric = g["friction_response"]
    topo = g["network_topology"]

    base_value = holder.limit_minor if amt["base"] == "limit" else holder.balance_minor
    steps = amt["steps"]

    # Provision devices and mule accounts up front, capped by the episode budget.
    device_pool: list[str] = []
    try:
        n_dev = min(device_policy["device_count"], budget["devices"])
        for d in range(int(n_dev)):
            ledger.allocate(episode_id, "devices", 1, budget["devices"])
            device_pool.append(f"{episode_id}_dev{d}")
        if budget["synthetic_identities"] > 0:
            ledger.allocate(episode_id, "synthetic_identities",
                            min(1, budget["synthetic_identities"]), budget["synthetic_identities"])
    except BudgetExhausted:
        pass
    if not device_pool:
        device_pool = holder.device_ids[:1] or [f"{episode_id}_dev0"]

    mule_payees: list[str] = []
    fanout = int(topo["mule_fanout"])
    for k in range(fanout):
        try:
            ledger.allocate(episode_id, "mule_accounts", 1, budget["mule_accounts"])
            mule_payees.append(f"mule_{episode_id}_{k}")
        except BudgetExhausted:
            break

    specs: list[SessionSpec] = []
    t = start_ts
    abandon = float(fric["abandon_prob"])

    def _device(i: int) -> str:
        reuse = device_policy["reuse"]
        if reuse == "victim_device" and holder.device_ids:
            return holder.device_ids[0]
        if reuse == "rotating":
            return device_pool[i % len(device_pool)]
        return device_pool[0]

    # Escalation ladder against the target.
    for i, step in enumerate(steps):
        try:
            ledger.allocate(episode_id, "operator_hours", _OP_HOURS_PER_TXN, budget["operator_hours"])
        except BudgetExhausted:
            return specs  # abort mid-episode; partial cost already recorded
        amount = max(1, int(float(step) * base_value))
        channel = _pick_channel(g["channel_mix"]["weights"], gen)
        payee = mule_payees[i % len(mule_payees)] if (mule_payees and channel != Channel.CARD_NOT_PRESENT) else None
        specs.append(
            SessionSpec(
                ts=t,
                cardholder_id=holder.cardholder_id,
                is_fraud=True,
                attack_id=genome.attack_id,
                genome_id=genome.genome_id,
                amount_minor=amount,
                channel=channel,
                payee_id=payee,
                device_id=_device(i),
                abandon_prob=abandon,
            )
        )
        t += float(gen.lognormal(timing["inter_txn_delay_mu"], timing["inter_txn_delay_sigma"]))

    # Fan-out cash-out after a dwell.
    t += timing["dwell_before_cashout_h"] * 3600.0
    cashout_amount = max(1, int(float(amt["max_fraction"]) * base_value / max(1, len(mule_payees))))
    for k, payee in enumerate(mule_payees):
        try:
            ledger.allocate(episode_id, "operator_hours", _OP_HOURS_PER_TXN, budget["operator_hours"])
        except BudgetExhausted:
            return specs
        specs.append(
            SessionSpec(
                ts=t + k * 60.0,
                cardholder_id=holder.cardholder_id,
                is_fraud=True,
                attack_id=genome.attack_id,
                genome_id=genome.genome_id,
                amount_minor=cashout_amount,
                channel=Channel.A2A,
                payee_id=payee,
                device_id=_device(k),
                abandon_prob=abandon,
            )
        )
    return specs
