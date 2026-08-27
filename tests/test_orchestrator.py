import json

from hydraloop.loop.ledger import GenerationLedger
from hydraloop.loop.orchestrator import run_loop

# A reply the strategist's repair tier accepts: a partial gene overlay, which is
# what a real model returns far more often than a complete genome.
_OVERLAY_REPLY = '{"genes": {"timing_policy": {"inter_txn_delay_mu": 0.6}}}'


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


def test_every_escaping_genome_can_be_named_on_the_lineage_screen(small_config):
    """Lineage showed "no brief recorded" for every node on a real run.

    Only the curated example shipped a genome manifest, and mutation mints a new
    id each generation, so nothing the loop actually simulated could be resolved
    to a family or a brief.
    """
    from hydraloop.api.ledger_source import genome_lineage

    summary_path = run_loop(small_config, run_id="test_loop_lineage", generations=2)
    manifest = json.loads(
        (summary_path.parent / "genomes.json").read_text(encoding="utf-8")
    )
    assert manifest, "no genome manifest written for the run"

    lineage = genome_lineage("test_loop_lineage")
    assert lineage["nodes"], "no escaping genomes to describe"

    by_id = {g["genome_id"]: g for g in manifest}
    for node in lineage["nodes"]:
        assert node["brief"], f"no brief for genome {node['genome_id']}"
        assert node["family"], f"no family for genome {node['genome_id']}"
        # The attack id, family and brief must all describe the same genome. The
        # cluster used to take its genome and its attack id as two independent
        # modes, which labelled nodes with an unrelated attack's family.
        entry = by_id[node["genome_id"]]
        assert entry["attack_id"] == node["attack_id"]
        assert entry["family"] == node["family"]


def test_loop_without_a_model_records_no_strategist_activity(small_config):
    """The offline default must not claim a model ran."""
    summary = json.loads(
        run_loop(small_config, run_id="test_loop_offline", generations=2).read_text(
            encoding="utf-8"
        )
    )

    strategist = summary["strategist"]
    assert strategist["provider"] == "none"
    assert strategist["available"] is False
    assert strategist["proposals"] == 0
    assert strategist["llm_authored"] == 0


def test_a_configured_model_actually_proposes_genomes_in_the_loop(small_config, tmp_path):
    """The claim under test: a client reaches the strategist inside run_loop.

    Nothing asserted this before, so the loop could have been silently
    deterministic while the documentation said a model could drive it.
    """
    calls: list[str] = []

    def model(prompt: str) -> str:
        calls.append(prompt)
        return _OVERLAY_REPLY

    summary_path = run_loop(
        small_config, run_id="test_loop_llm", generations=3, llm=model
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert calls, "run_loop never called the model it was given"
    # Generation 1 has no parent population to evolve, so proposals start at 2.
    assert summary["strategist"]["proposals"] == len(calls)
    assert summary["strategist"]["provider"] == "custom"
    assert summary["strategist"]["accepted"] >= 1

    # The audit file is what the Strategist screen reads; without it that screen
    # falls back to a committed example and shows another run's numbers.
    audit = json.loads(
        (summary_path.parent / "strategist_audit.json").read_text(encoding="utf-8")
    )
    assert audit["proposals"] == len(calls)
    assert audit["llm_authored"] >= 1, "no proposal was attributed to the model"
    assert audit["samples"], "the screen would have nothing to show"

    # Every prompt must ask for simulator parameters, never for attack content.
    assert all("JSON ONLY" in p and "credentials" in p for p in calls)


def test_a_refusing_model_does_not_break_the_loop(small_config):
    """A model that returns junk must cost a mutation, not the run."""
    summary_path = run_loop(
        small_config, run_id="test_loop_refuse", generations=2, llm=lambda _p: "not json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["ledger_entries"] == 2
    assert summary["strategist"]["refused"] >= 1
    assert summary["strategist"]["llm_authored"] == 0
    GenerationLedger.load(summary_path.parent / "generation_ledger.jsonl").verify()
