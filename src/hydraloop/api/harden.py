"""The closed loop, on demand: let an attack escape, harden, then re-attack.

This is the demo that shows the loop actually closing. It is deliberately
structured so the result cannot be an artefact of training on the test rows:

  * The incumbent detector is trained on *other* attack families only, so the
    threat the user describes is a genuine zero-day to it.
  * Wave 1 of that threat is scored by the incumbent. Whatever slips under the
    operating threshold is an escape.
  * The escapes enter immune memory and a candidate is retrained, but it is only
    allowed to learn from rows whose disputes have *matured* -- the same label
    delay a real issuer lives with.
  * The candidate must clear the regression gauntlet against the older families
    before it is allowed to count as promoted.
  * The verdict is measured on wave 2: the same genome, a fresh population and
    fresh draws, rows neither model has ever seen. Both models are compared at
    their own threshold calibrated to the same 1% FPR budget, so the comparison
    cannot be won by simply flagging more traffic.

Every number the UI displays comes from this function.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pandas as pd

from ..blue.detector import Detector
from ..catalog.loader import load_catalog
from ..config import Config, SimulationConfig
from ..loop.gauntlet import run_gauntlet
from ..loop.immune_memory import ImmuneMemory
from ..loop.ledger import GenerationLedger
from ..paths import REPORTS_DIR
from ..red.discover import discover_threat
from ..red.dsl.genome import Genome, genome_from_template
from ..red.holdout import is_holdout
from ..red.mixer import build_attack_specs
from ..twin.population import SECONDS_PER_DAY
from ..twin.run import build_engine, legit_session_specs
from .lab import _genome_from_discovery

FPR_BUDGET = 0.01

# Seeds are fixed so a judge can re-run the demo and get the same story, but each
# wave uses a different seed so it is an independent draw of population, arrival
# times and victim selection.
SEED_CALIB = 5
SEED_BASELINE = 11
SEED_WAVE1 = 23
SEED_WAVE2 = 47

# The operating threshold is a 1-in-100 quantile, so it needs a legit sample large
# enough for that quantile to mean something. A few hundred rows would put the
# threshold on top of two or three transactions and the realised FPR would not
# survive contact with fresh traffic.
CALIB_LEGIT = 2500
BASELINE_LEGIT = 1200
BASELINE_FRAUD = 150
WAVE_LEGIT = 1200
WAVE_FRAUD = 120


def _wave_config(seed: int, legit: int, fraud: int) -> Config:
    sim = SimulationConfig(
        seed=seed,
        generations=1,
        legitimate_transactions_per_generation=legit,
        attack_episodes_per_generation=fraud,
        fraud_rate_target=0.1,
        horizon_days=10,
        label_delay_hours_mean=0.5,
        label_delay_hours_std=0.2,
    )
    return Config(raw={"harden": True, "seed": seed}, simulation=sim)


def _simulate(cfg: Config, genomes: list[Genome], stream: str) -> pd.DataFrame:
    engine, registry = build_engine(cfg)
    horizon_s = cfg.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(
        cfg, engine, registry, cfg.simulation.legitimate_transactions_per_generation
    )
    fraud, _ = build_attack_specs(
        engine,
        registry,
        genomes,
        cfg.simulation.attack_episodes_per_generation,
        horizon_s,
        stream,
    )
    df = pd.DataFrame(engine.simulate(legit + fraud).transactions)
    if df.empty:
        return df
    return df.sort_values("ts").reset_index(drop=True)


def _known_genomes(exclude_family: str) -> list[Genome]:
    """Real catalog genomes from every family except the one under test."""
    out: list[Genome] = []
    for s in load_catalog():
        if not s.evolvable or is_holdout(s.attack_id) or s.family == exclude_family:
            continue
        out.append(genome_from_template(s.family, s.attack_id, s.genome_template))
    return out


def _raw_scores(detector: Detector, df: pd.DataFrame) -> np.ndarray:
    """The uncalibrated model score, used for every flag/no-flag decision.

    Isotonic calibration is monotone, so this preserves the ranking exactly while
    staying free of the score ties that make a 1-in-100 operating point
    unreachable on a calibrated output. Calibrated probabilities are still what
    the UI displays -- they are the honest risk estimate; this is just the knob
    the threshold turns.
    """
    return detector.score_raw(df)


def _threshold_at_fpr(scores: np.ndarray, fpr: float = FPR_BUDGET) -> float:
    """Lowest threshold whose realised FPR on this sample stays inside the budget."""
    if len(scores) == 0:
        return 0.5
    unique = np.unique(scores)
    for candidate in unique:
        if float(np.mean(scores >= candidate)) <= fpr:
            return float(candidate)
    return float(np.nextafter(unique[-1], np.inf))


def _temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-ordered train / calibrate split -- never a random shuffle."""
    cut = int(len(df) * 0.75)
    return df.iloc[:cut].reset_index(drop=True), df.iloc[cut:].reset_index(drop=True)


def _rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _ledger_path():
    path = REPORTS_DIR / "lab"
    path.mkdir(parents=True, exist_ok=True)
    return path / "harden_ledger.jsonl"


def iter_harden(text: str) -> Iterator[dict[str, Any]]:
    """Stream the escape -> harden -> re-attack cycle as it computes."""
    text = (text or "").strip()[:600]
    if len(text) < 12:
        raise ValueError("describe the threat in a short paragraph (behaviour only)")

    rng = np.random.default_rng(SEED_BASELINE)
    disc = discover_threat(text, rng, llm=None)
    new_genome = _genome_from_discovery(disc)
    known = _known_genomes(disc["family"])

    yield {
        "type": "identity",
        "family": disc["family"],
        "attack_name": disc["attack_name"],
        "genome_id": disc["genome_id"],
        "brief": disc["brief"],
        "known_families": sorted({g.family for g in known}),
        "known_genomes": len(known),
    }

    # ---- 1. The incumbent: trained on the families we already know about -----
    yield {
        "type": "status",
        "phase": "incumbent",
        "message": (
            f"Training the incumbent detector on {len(known)} known attack genomes "
            f"from {len(set(g.family for g in known))} other families. It will never "
            f"see '{disc['family']}' before the attack lands."
        ),
    }
    base_cfg = _wave_config(SEED_BASELINE, BASELINE_LEGIT, BASELINE_FRAUD)
    base_df = _simulate(base_cfg, known, "harden:baseline")
    if base_df.empty or not base_df["is_fraud"].any():
        raise RuntimeError("baseline wave produced no fraud; cannot build an incumbent")

    base_train, base_val = _temporal_split(base_df)
    incumbent = Detector(seed=SEED_BASELINE).fit(base_train, base_val)

    # An independent legit-only wave sets the operating threshold for *both*
    # models, so neither is scored against a threshold fitted to its own training
    # traffic and the 1% budget is measured on the same footing.
    yield {
        "type": "status",
        "phase": "incumbent",
        "message": (
            f"Calibrating the operating threshold on {CALIB_LEGIT} legitimate "
            "transactions from an independent wave, held out from all training."
        ),
    }
    calib_df = _simulate(_wave_config(SEED_CALIB, CALIB_LEGIT, 0), [], "harden:calib")
    thr_legit = calib_df[~calib_df["is_fraud"]].reset_index(drop=True)
    inc_thr = _threshold_at_fpr(_raw_scores(incumbent, thr_legit))
    archive_fraud = base_df[base_df["is_fraud"]].reset_index(drop=True)
    inc_archive_recall = _rate(
        int((_raw_scores(incumbent, archive_fraud) >= inc_thr).sum()), len(archive_fraud)
    )

    yield {
        "type": "incumbent",
        "n_txns": int(len(base_df)),
        "n_fraud": int(base_df["is_fraud"].sum()),
        "train_rows": int(len(base_train)),
        "calib_rows": int(len(thr_legit)),
        "threshold": inc_thr,
        "archive_recall": inc_archive_recall,
        "detail": (
            f"Incumbent live at a {FPR_BUDGET:.0%} false-positive budget "
            f"(threshold {inc_thr:.3f}, set on {len(thr_legit)} held-out legitimate "
            f"transactions). It catches {inc_archive_recall:.0%} of the attacks it "
            "already knows."
        ),
    }

    # ---- 2. Wave 1: the new attack lands and some of it escapes -------------
    yield {
        "type": "status",
        "phase": "escape",
        "message": f"Wave 1: releasing the '{disc['family']}' genome against the live incumbent.",
    }
    w1_cfg = _wave_config(SEED_WAVE1, WAVE_LEGIT, WAVE_FRAUD)
    w1_df = _simulate(w1_cfg, [new_genome], "harden:wave1")
    if w1_df.empty or not w1_df["is_fraud"].any():
        raise RuntimeError("wave 1 produced no attack transactions")

    w1 = w1_df.copy()
    w1["flag"] = _raw_scores(incumbent, w1_df)
    w1["risk"] = incumbent.score(w1_df)
    w1_fraud = w1[w1["is_fraud"]]
    w1_escaped = w1_fraud[w1_fraud["flag"] < inc_thr]

    yield {
        "type": "escape",
        "n_fraud": int(len(w1_fraud)),
        "escaped": int(len(w1_escaped)),
        "caught": int(len(w1_fraud) - len(w1_escaped)),
        "recall": _rate(int(len(w1_fraud) - len(w1_escaped)), int(len(w1_fraud))),
        "escaped_value_minor": float(w1_escaped["amount_minor"].sum()),
        "samples": [
            {
                "txn_id": str(r["txn_id"]),
                "amount_minor": float(r["amount_minor"]),
                "score": float(r["risk"]),
            }
            for _, r in w1_escaped.nlargest(6, "amount_minor").iterrows()
        ],
        "detail": (
            f"{len(w1_escaped)} of {len(w1_fraud)} attack transactions escaped the "
            f"incumbent, worth {w1_escaped['amount_minor'].sum() / 100:,.0f} in value."
        ),
    }

    # ---- 3. Harden: escapes enter immune memory, candidate retrains ---------
    yield {
        "type": "status",
        "phase": "harden",
        "message": (
            "Adding wave 1 to immune memory and retraining a candidate. It may only "
            "learn from transactions whose disputes have already matured."
        ),
    }
    memory = ImmuneMemory(seed=SEED_BASELINE)
    memory.add_generation(base_train, 1)
    memory.add_generation(w1_df, 2)
    cand_train = memory.training_frame()
    candidate = Detector(seed=SEED_BASELINE).fit(cand_train, base_val)
    cand_thr = _threshold_at_fpr(_raw_scores(candidate, thr_legit))

    yield {
        "type": "candidate",
        "train_rows": int(len(cand_train)),
        "memory_rows": int(len(memory.all_data())),
        "threshold": cand_thr,
        "detail": (
            f"Candidate trained on {len(cand_train)} retained rows across 2 generations, "
            f"re-calibrated to the same {FPR_BUDGET:.0%} FPR budget (threshold {cand_thr:.3f})."
        ),
    }

    # ---- 4. The gauntlet: it must not regress on what we already caught -----
    yield {
        "type": "status",
        "phase": "gauntlet",
        "message": (
            f"Regression gauntlet: the candidate must hold recall on all "
            f"{len(archive_fraud)} archived attacks from the older families."
        ),
    }
    gres = run_gauntlet(
        incumbent,
        candidate,
        legit_val_df=thr_legit,
        archive_fraud_df=archive_fraud,
        fpr_target=FPR_BUDGET,
    )
    yield {
        "type": "gauntlet",
        "promote": bool(gres.promote),
        "reason": gres.reason,
        "incumbent_recall": float(gres.incumbent_recall),
        "candidate_recall": float(gres.candidate_recall),
        "candidate_fpr": float(gres.candidate_fpr),
        "candidate_ece": float(gres.candidate_ece),
    }

    # ---- 5. Wave 2: the same attack, rows neither model has seen ------------
    yield {
        "type": "status",
        "phase": "verdict",
        "message": (
            "Wave 2: the same genome against a fresh population. Neither model has "
            "seen these transactions. Both judged at the same FPR budget."
        ),
    }
    w2_cfg = _wave_config(SEED_WAVE2, WAVE_LEGIT, WAVE_FRAUD)
    w2_df = _simulate(w2_cfg, [new_genome], "harden:wave2")
    if w2_df.empty or not w2_df["is_fraud"].any():
        raise RuntimeError("wave 2 produced no attack transactions")

    w2 = w2_df.copy()
    w2["flag_before"] = _raw_scores(incumbent, w2_df)
    w2["flag_after"] = _raw_scores(candidate, w2_df)
    w2["before"] = incumbent.score(w2_df)
    w2["after"] = candidate.score(w2_df)
    w2["hit_before"] = w2["flag_before"] >= inc_thr
    w2["hit_after"] = w2["flag_after"] >= cand_thr
    w2_fraud = w2[w2["is_fraud"]]
    w2_legit = w2[~w2["is_fraud"]]

    caught_before = int(w2_fraud["hit_before"].sum())
    caught_after = int(w2_fraud["hit_after"].sum())
    fp_before = int(w2_legit["hit_before"].sum())
    fp_after = int(w2_legit["hit_after"].sum())
    n_f, n_l = int(len(w2_fraud)), int(len(w2_legit))

    value_escaped_before = float(w2_fraud[~w2_fraud["hit_before"]]["amount_minor"].sum())
    value_escaped_after = float(w2_fraud[~w2_fraud["hit_after"]]["amount_minor"].sum())

    before = {
        "recall": _rate(caught_before, n_f),
        "caught": caught_before,
        "escaped": n_f - caught_before,
        "false_positives": fp_before,
        "fpr": _rate(fp_before, n_l),
        "escaped_value_minor": value_escaped_before,
        "threshold": inc_thr,
    }
    after = {
        "recall": _rate(caught_after, n_f),
        "caught": caught_after,
        "escaped": n_f - caught_after,
        "false_positives": fp_after,
        "fpr": _rate(fp_after, n_l),
        "escaped_value_minor": value_escaped_after,
        "threshold": cand_thr,
    }

    movers = w2_fraud.assign(delta=w2_fraud["after"] - w2_fraud["before"])
    txns = [
        {
            "txn_id": str(r["txn_id"]),
            "amount_minor": float(r["amount_minor"]),
            "before": float(r["before"]),
            "after": float(r["after"]),
            "caught_before": bool(r["hit_before"]),
            "caught_after": bool(r["hit_after"]),
        }
        for _, r in movers.nlargest(12, "delta").iterrows()
    ]

    yield {
        "type": "verdict",
        "n_fraud": n_f,
        "n_legit": n_l,
        "before": before,
        "after": after,
        "newly_caught": max(0, caught_after - caught_before),
        "value_recovered_minor": max(0.0, value_escaped_before - value_escaped_after),
        "txns": txns,
    }

    # ---- 6. Write it to the tamper-evident ledger ---------------------------
    ledger = GenerationLedger.load(_ledger_path())
    entry = ledger.append(
        {
            "generation": len(ledger.entries) + 1,
            "kind": "on_demand_harden",
            "genome_id": disc["genome_id"],
            "family": disc["family"],
            "promoted": bool(gres.promote),
            "gauntlet_reason": gres.reason,
            "wave1_escapes": int(len(w1_escaped)),
            "wave2_recall_before": before["recall"],
            "wave2_recall_after": after["recall"],
            "wave2_fpr_before": before["fpr"],
            "wave2_fpr_after": after["fpr"],
            "config_hash": w2_cfg.config_hash,
        }
    )
    yield {
        "type": "ledger",
        "entry_hash": entry["entry_hash"],
        "prev_hash": entry["prev_hash"],
        "generation": entry["payload"]["generation"],
        "chain_length": len(ledger.entries),
    }

    yield {
        "type": "done",
        "result": {
            "family": disc["family"],
            "attack_name": disc["attack_name"],
            "genome_id": disc["genome_id"],
            "brief": disc["brief"],
            "promoted": bool(gres.promote),
            "gauntlet_reason": gres.reason,
            "wave1": {
                "n_fraud": int(len(w1_fraud)),
                "escaped": int(len(w1_escaped)),
                "recall": _rate(int(len(w1_fraud) - len(w1_escaped)), int(len(w1_fraud))),
            },
            "before": before,
            "after": after,
            "n_fraud": n_f,
            "n_legit": n_l,
            "newly_caught": max(0, caught_after - caught_before),
            "value_recovered_minor": max(0.0, value_escaped_before - value_escaped_after),
            "txns": txns,
            "entry_hash": entry["entry_hash"],
        },
    }


def run_harden(text: str) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    for event in iter_harden(text):
        if event.get("type") == "done":
            result = event["result"]
    if result is None:
        raise RuntimeError("harden cycle produced no result")
    return result
