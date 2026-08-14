"""Leave-one-family-out transfer: a 6x6 train-on-i, test-on-j recall matrix.

The diagonal is in-family detection; the off-diagonal is transfer to a family the
model never trained on. The weak cells are reported rather than hidden, because
they are the honest answer to "which novel family would still get through".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..blue.features import mature_mask, true_labels
from ..config import Config
from ..evaluation.metrics import threshold_at_fpr
from ..red.dsl.genome import genome_from_template
from ..red.dsl.spec import FAMILIES
from ..red.mixer import build_attack_specs
from ..twin.population import SECONDS_PER_DAY
from ..twin.run import build_engine, legit_session_specs


def build_family_frames(cfg: Config, fraud_per_family: int = 60) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    from ..catalog import load_catalog
    from ..red.holdout import is_holdout

    engine, registry = build_engine(cfg)
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(cfg, engine, registry, cfg.simulation.legitimate_transactions_per_generation)

    by_family: dict[str, list] = {f: [] for f in FAMILIES}
    attack_family: dict[str, str] = {}
    for s in load_catalog():
        if not s.evolvable or is_holdout(s.attack_id):
            continue
        by_family[s.family].append(genome_from_template(s.family, s.attack_id, s.genome_template))
        attack_family[s.attack_id] = s.family

    fraud_specs = []
    for fam, genomes in by_family.items():
        if not genomes:
            continue
        specs, _ = build_attack_specs(engine, registry, genomes, fraud_per_family, horizon_s, f"lofo:{fam}")
        fraud_specs.extend(specs)

    tx = pd.DataFrame(engine.simulate(legit + fraud_specs).transactions)
    tx["family"] = tx["attack_id"].map(attack_family)
    legit_df = tx[~tx["is_fraud"]].reset_index(drop=True)
    frauds = {
        fam: tx[(tx["is_fraud"]) & (tx["family"] == fam)].reset_index(drop=True)
        for fam in FAMILIES
        if ((tx["is_fraud"]) & (tx["family"] == fam)).any()
    }
    return legit_df, frauds


def transfer_matrix(legit_df: pd.DataFrame, family_frauds: dict[str, pd.DataFrame],
                    seed: int = 42, fpr_target: float = 0.01) -> dict:
    families = [f for f in FAMILIES if f in family_frauds]
    legit_df = legit_df.sort_values("ts").reset_index(drop=True)
    cut = int(len(legit_df) * 0.7)
    legit_train, legit_test = legit_df.iloc[:cut], legit_df.iloc[cut:]

    matrix = np.zeros((len(families), len(families)))
    for i, fam_i in enumerate(families):
        train = pd.concat([legit_train, family_frauds[fam_i]], ignore_index=True).sort_values("ts")
        vcut = int(len(train) * 0.85)
        detector = Detector(seed=seed).fit(train.iloc[:vcut], train.iloc[vcut:])
        legit_scores = detector.score(legit_test)
        thr = threshold_at_fpr(np.zeros(len(legit_scores), dtype=int), legit_scores, fpr_target)
        for j, fam_j in enumerate(families):
            test_j = family_frauds[fam_j]
            ev = test_j[mature_mask(test_j) & true_labels(test_j).astype(bool)]
            if ev.empty:
                matrix[i, j] = float("nan")
                continue
            matrix[i, j] = float(np.mean(detector.score(ev) >= thr))

    weak_cells = []
    for i, fam_i in enumerate(families):
        for j, fam_j in enumerate(families):
            if i != j and not np.isnan(matrix[i, j]) and matrix[i, j] < 0.3:
                weak_cells.append({"train": fam_i, "test": fam_j, "recall": round(matrix[i, j], 4)})

    return {
        "families": families,
        "matrix": [[None if np.isnan(v) else round(float(v), 4) for v in row] for row in matrix],
        "weak_cells": weak_cells,
    }
