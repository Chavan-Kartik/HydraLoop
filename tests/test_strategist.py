import json

import numpy as np

from hydraloop.red.dsl.genome import default_genome
from hydraloop.red.strategist import Strategist


def test_offline_planner_emits_valid_genome():
    strat = Strategist(rng=np.random.default_rng(0))
    parent = default_genome()
    child = strat.propose(parent, {"escape_cluster": "AF-09"})
    child.validate()  # must not raise
    assert strat.audit_log[-1].accepted
    assert not strat.refusals()


def test_invalid_llm_output_is_refused_and_falls_back():
    strat = Strategist(rng=np.random.default_rng(0), llm=lambda _p: "this is not json")
    child = strat.propose(default_genome())
    child.validate()
    assert len(strat.refusals()) == 1
    assert "refused" in strat.refusals()[0].reason


def test_valid_llm_output_is_accepted():
    good = default_genome()
    strat = Strategist(rng=np.random.default_rng(0), llm=lambda _p: json.dumps(good.to_dict()))
    child = strat.propose(default_genome())
    assert child.genome_id == good.genome_id
    assert strat.audit_log[-1].accepted
    assert "validated" in strat.audit_log[-1].reason
