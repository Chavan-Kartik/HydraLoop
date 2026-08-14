import numpy as np
import pandas as pd

from hydraloop.loop.immune_memory import ImmuneMemory


def _frame(n, fraud_frac, channel="A2A"):
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "txn_id": [f"t{i}" for i in range(n)],
            "is_fraud": rng.random(n) < fraud_frac,
            "channel": channel,
            "amount_minor": rng.integers(1000, 50000, n),
        }
    )


def test_replay_archive_is_fraud_only():
    mem = ImmuneMemory()
    mem.add_generation(_frame(100, 0.2), 1)
    mem.add_generation(_frame(100, 0.2), 2)
    archive = mem.replay_archive()
    assert archive["is_fraud"].all()
    assert (archive["generation"].isin([1, 2])).all()


def test_stratified_subsample_keeps_all_fraud_and_caps_rows():
    mem = ImmuneMemory(max_rows=200)
    for g in range(1, 6):
        mem.add_generation(_frame(300, 0.1, channel="A2A" if g % 2 else "WALLET"), g)
    frame = mem.training_frame()
    assert len(frame) <= 200 + frame["is_fraud"].sum()  # all fraud retained
    assert frame["is_fraud"].sum() == mem.all_data()["is_fraud"].sum()
