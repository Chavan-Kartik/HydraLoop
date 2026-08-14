"""Resource accounting for attacks.

Every attack consumes finite resources (mule accounts, synthetic identities,
devices, operator hours). The ledger records consumption against each episode's
budget and refuses allocations that would exceed it, so an episode that runs out
of budget mid-way aborts and records only what it actually spent. Phase 9's
economics reads these totals, so the ledger must balance exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RESOURCE_KINDS = ("mule_accounts", "synthetic_identities", "devices", "operator_hours")


class BudgetExhausted(Exception):
    """Raised when an episode requests more of a resource than its budget allows."""


@dataclass
class EpisodeBudget:
    mule_accounts: int
    synthetic_identities: int
    devices: int
    operator_hours: float


@dataclass
class ResourceLedger:
    entries: list[dict] = field(default_factory=list)
    _spent: dict[tuple[str, str], float] = field(default_factory=dict)

    def spent(self, episode_id: str, kind: str) -> float:
        return self._spent.get((episode_id, kind), 0.0)

    def allocate(self, episode_id: str, kind: str, amount: float, budget: float) -> float:
        if kind not in RESOURCE_KINDS:
            raise ValueError(f"unknown resource kind {kind!r}")
        already = self.spent(episode_id, kind)
        if already + amount > budget + 1e-9:
            raise BudgetExhausted(
                f"episode {episode_id}: {kind} {already + amount} exceeds budget {budget}"
            )
        self._spent[(episode_id, kind)] = already + amount
        self.entries.append({"episode_id": episode_id, "kind": kind, "amount": amount})
        return amount

    def totals(self) -> dict[str, float]:
        out = {k: 0.0 for k in RESOURCE_KINDS}
        for e in self.entries:
            out[e["kind"]] += e["amount"]
        return out

    def balances(self) -> bool:
        """The recomputed totals from entries must equal the running tallies."""
        recomputed = {k: 0.0 for k in RESOURCE_KINDS}
        for e in self.entries:
            recomputed[e["kind"]] += e["amount"]
        summed = {k: 0.0 for k in RESOURCE_KINDS}
        for (_, kind), amt in self._spent.items():
            summed[kind] += amt
        return all(abs(recomputed[k] - summed[k]) < 1e-6 for k in RESOURCE_KINDS)
