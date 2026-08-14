"""Bounded mutation of a genome.

Every perturbation is clamped back into the gene's declared range, so a mutated
genome is valid by construction. Mutation records the parent's id for lineage.
"""

from __future__ import annotations

import copy

import numpy as np

from .genome import Genome
from .spec import GENE_SPEC, GeneField


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _mutate_value(spec: GeneField, value, gen: np.random.Generator):
    if spec.kind == "float":
        span = spec.hi - spec.lo
        return _clamp(value + float(gen.normal(0.0, 0.15 * span)), spec.lo, spec.hi)
    if spec.kind == "int":
        step = int(round(float(gen.normal(0.0, max(1.0, 0.1 * (spec.hi - spec.lo))))))
        return int(_clamp(value + step, spec.lo, spec.hi))
    if spec.kind == "bool":
        return not value
    if spec.kind == "categorical":
        return spec.options[int(gen.integers(0, len(spec.options)))]
    if spec.kind == "simplex":
        keys = list(spec.members)
        base = np.array([max(1e-6, value[k]) for k in keys])
        noisy = base * np.exp(gen.normal(0.0, 0.4, size=len(keys)))
        noisy = noisy / noisy.sum()
        return {k: float(w) for k, w in zip(keys, noisy, strict=True)}
    if spec.kind == "fraction_ladder":
        span = spec.hi - spec.lo
        steps = [_clamp(v + float(gen.normal(0.0, 0.1 * span)), spec.lo, spec.hi) for v in value]
        return sorted(steps)
    raise ValueError(f"unknown gene kind {spec.kind}")


def mutate(genome: Genome, gen: np.random.Generator, rate: float = 0.2) -> Genome:
    genes = copy.deepcopy(genome.genes)
    for group, fields in GENE_SPEC.items():
        for name, spec in fields.items():
            if gen.random() < rate:
                genes[group][name] = _mutate_value(spec, genes[group][name], gen)
    # Preserve the semantic constraint the validator enforces.
    vs = genes["victim_selection"]
    if vs["balance_percentile_lo"] > vs["balance_percentile_hi"]:
        vs["balance_percentile_lo"], vs["balance_percentile_hi"] = (
            vs["balance_percentile_hi"],
            vs["balance_percentile_lo"],
        )
    child = Genome(
        family=genome.family,
        genes=genes,
        attack_id=genome.attack_id,
        parent_id=genome.genome_id,
    )
    child.validate()
    return child
