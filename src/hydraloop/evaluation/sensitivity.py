"""Sensitivity sweeps at +/-50% over registered assumptions, with a tornado plot.

Every assumed parameter is swept to both ends of its declared range while the
rest stay at base; the resulting swing in the target metric ranks the
assumptions by influence. The tornado plot makes it obvious which assumptions the
conclusions actually depend on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


@dataclass(frozen=True)
class Assumption:
    name: str
    base: float
    low: float
    high: float

    @staticmethod
    def pm50(name: str, base: float) -> Assumption:
        return Assumption(name, base, base * 0.5, base * 1.5)


@dataclass
class TornadoRow:
    name: str
    low_metric: float
    high_metric: float
    base_metric: float

    @property
    def swing(self) -> float:
        return abs(self.high_metric - self.low_metric)


def sweep(
    metric_fn: Callable[[dict[str, float]], float],
    assumptions: list[Assumption],
    base_params: dict[str, float],
) -> list[TornadoRow]:
    base_metric = metric_fn(base_params)
    rows: list[TornadoRow] = []
    for a in assumptions:
        low_params = {**base_params, a.name: a.low}
        high_params = {**base_params, a.name: a.high}
        rows.append(
            TornadoRow(a.name, metric_fn(low_params), metric_fn(high_params), base_metric)
        )
    rows.sort(key=lambda r: r.swing, reverse=True)
    return rows


def plot_tornado(rows: list[TornadoRow], path: Path, metric_name: str = "metric") -> Path:
    base = rows[0].base_metric if rows else 0.0
    names = [r.name for r in rows][::-1]
    lows = [r.low_metric - base for r in rows][::-1]
    highs = [r.high_metric - base for r in rows][::-1]
    y = range(len(names))
    fig, ax = plt.subplots(figsize=(6, max(2, 0.5 * len(names))))
    ax.barh(list(y), [h - 0 for h in highs], left=0, color="#4cc9f0", label="high")
    ax.barh(list(y), [low for low in lows], left=0, color="#ff5c7a", label="low")
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.axvline(0, color="#333")
    ax.set_xlabel(f"change in {metric_name} vs base ({base:.3f})")
    ax.set_title("Sensitivity tornado (+/-50%)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
