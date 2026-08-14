
import pandas as pd
import pytest

from hydraloop.paths import REPO_ROOT
from hydraloop.red.holdout import HOLDOUT_ATTACK_IDS, is_holdout, load_holdout


def test_holdout_ids_span_four_scenarios():
    assert len(HOLDOUT_ATTACK_IDS) == 4
    assert is_holdout("AF-06")
    assert not is_holdout("AF-09")


def test_load_holdout_sealed_by_default(monkeypatch):
    monkeypatch.delenv("HYDRALOOP_ALLOW_HOLDOUT", raising=False)
    with pytest.raises(PermissionError):
        load_holdout()


def test_load_holdout_opens_with_flag(monkeypatch, tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    p = tmp_path / "transactions_holdout.parquet"
    df.to_parquet(p, index=False)
    monkeypatch.setenv("HYDRALOOP_ALLOW_HOLDOUT", "1")
    out = load_holdout(p)
    assert len(out) == 2


def test_no_training_module_sets_holdout_flag():
    # The env flag may only be referenced by the holdout guard and by tests.
    src = REPO_ROOT / "src" / "hydraloop"
    offenders = []
    for path in src.rglob("*.py"):
        if path.name == "holdout.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "HYDRALOOP_ALLOW_HOLDOUT" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"holdout flag referenced outside guard: {offenders}"


def test_holdout_data_excluded_from_training_splits():
    # If a run has produced splits, none may contain a holdout attack id.
    runs = sorted((REPO_ROOT / "reports" / "runs").glob("*/transactions_train.parquet"))
    if not runs:
        pytest.skip("no attack run present")
    df = pd.read_parquet(runs[-1])
    assert not df["attack_id"].apply(is_holdout).any()
