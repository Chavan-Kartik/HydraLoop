"""Immune memory: every attack from every prior generation is retained.

Once replay grows large, the archive is subsampled with a documented stratified
scheme (stratify by attack family and generation, keep all fraud, cap legit),
rather than a hidden or uniform sample that would quietly bias the gauntlet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class ImmuneMemory:
    def __init__(self, max_rows: int = 60000, seed: int = 42) -> None:
        self.max_rows = max_rows
        self.seed = seed
        self._frames: list[pd.DataFrame] = []

    def add_generation(self, df: pd.DataFrame, generation: int) -> None:
        tagged = df.copy()
        tagged["generation"] = generation
        self._frames.append(tagged)

    def all_data(self) -> pd.DataFrame:
        if not self._frames:
            return pd.DataFrame()
        return pd.concat(self._frames, ignore_index=True)

    def replay_archive(self) -> pd.DataFrame:
        """Fraud from all prior generations, used by the regression gauntlet."""
        df = self.all_data()
        if df.empty:
            return df
        return df[df["is_fraud"]].reset_index(drop=True)

    def training_frame(self) -> pd.DataFrame:
        """All retained data, stratified-subsampled if it exceeds the cap."""
        df = self.all_data()
        if len(df) <= self.max_rows or df.empty:
            return df
        rng = np.random.default_rng(self.seed)
        fraud = df[df["is_fraud"]]
        legit = df[~df["is_fraud"]]
        legit_budget = max(0, self.max_rows - len(fraud))
        # Stratify legit by (generation, channel) so no stratum is dropped wholesale.
        keep_idx: list[int] = []
        groups = list(legit.groupby(["generation", "channel"]))
        per_group = max(1, legit_budget // max(1, len(groups)))
        for _, grp in groups:
            take = min(len(grp), per_group)
            keep_idx.extend(rng.choice(grp.index.to_numpy(), size=take, replace=False).tolist())
        kept_legit = legit.loc[keep_idx]
        return pd.concat([fraud, kept_legit], ignore_index=True)
