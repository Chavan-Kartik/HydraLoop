import json

from hydraloop.loop.ledger import GenerationLedger
from hydraloop.loop.orchestrator import run_loop


def test_loop_runs_unattended_and_seals_the_ledger(small_config):
    summary_path = run_loop(
        small_config, run_id="test_loop", generations=3, rollback_demo_generation=2
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["generations"] == 3
    assert summary["ledger_entries"] == 3
    # The ledger reconstructs from disk and passes its own integrity check.
    reloaded = GenerationLedger.load(summary_path.parent / "generation_ledger.jsonl")
    assert len(reloaded.entries) == 3
    reloaded.verify()

    # DoD: at least one real escape closed and at least one gauntlet rollback.
    assert summary["escapes_closed_total"] >= 1
    assert summary["rollbacks"] >= 1
