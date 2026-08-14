"""Zero-day holdout enforcement.

Four scenarios never enter training. They are physically separated on disk under
``data/holdout_zeroday/`` and the loader refuses to read them unless an explicit
environment flag is set. Filesystem separation plus a code guard, because a
promise not to peek is not a control. A test asserts no training module sets the
flag.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from ..paths import HOLDOUT_DIR

HOLDOUT_ATTACK_IDS = frozenset({"AF-06", "AF-13", "AF-18", "AF-22"})
_ALLOW_ENV = "HYDRALOOP_ALLOW_HOLDOUT"


def is_holdout(attack_id: str | None) -> bool:
    return attack_id in HOLDOUT_ATTACK_IDS


def holdout_allowed() -> bool:
    return os.environ.get(_ALLOW_ENV) == "1"


def load_holdout(path: Path | None = None) -> pd.DataFrame:
    if not holdout_allowed():
        raise PermissionError(
            f"zero-day holdout is sealed; set {_ALLOW_ENV}=1 only for final evaluation"
        )
    path = path or (HOLDOUT_DIR / "transactions_holdout.parquet")
    return pd.read_parquet(path)


@contextmanager
def final_evaluation_access() -> Iterator[None]:
    """Temporarily unseal the holdout for a final-evaluation read only.

    The unseal flag is manipulated exclusively here, inside the guard, so that no
    training module ever names it. The previous environment is always restored.
    """
    prev = os.environ.get(_ALLOW_ENV)
    os.environ[_ALLOW_ENV] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(_ALLOW_ENV, None)
        else:
            os.environ[_ALLOW_ENV] = prev


def load_holdout_final(path: Path | None = None) -> pd.DataFrame:
    """Read the zero-day holdout for final evaluation, unsealing within the guard."""
    with final_evaluation_access():
        return load_holdout(path)
