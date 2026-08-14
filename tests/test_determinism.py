from hydraloop.twin.run import build_engine, legit_session_specs
from hydraloop.twin.writer import canonical_digest


def _digest(cfg, target=250):
    engine, registry = build_engine(cfg)
    specs = legit_session_specs(cfg, engine, registry, target)
    result = engine.simulate(specs)
    return canonical_digest(result.transactions), len(result.transactions)


def test_golden_run_digest(small_config):
    d1, n1 = _digest(small_config)
    d2, n2 = _digest(small_config)
    assert n1 == n2
    assert n1 > 0
    assert d1 == d2  # same seed -> identical canonical digest
