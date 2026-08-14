from hydraloop.twin.population import build_population
from hydraloop.twin.rng import RngRegistry


def test_population_is_deterministic():
    p1 = build_population(RngRegistry(11), 50, 10)
    p2 = build_population(RngRegistry(11), 50, 10)
    assert [c.balance_minor for c in p1.cardholders] == [c.balance_minor for c in p2.cardholders]
    assert [m.mcc for m in p1.merchants] == [m.mcc for m in p2.merchants]


def test_merchant_weights_sum_to_one():
    p = build_population(RngRegistry(3), 40, 15)
    assert abs(float(p.merchant_weights.sum()) - 1.0) < 1e-9


def test_inactive_entities_allowed():
    # A cardholder with a very low rate can legitimately produce no traffic;
    # the population must still contain them with valid (empty-history) state.
    p = build_population(RngRegistry(5), 30, 8)
    assert all(c.device_ids for c in p.cardholders)
    assert p.n_cardholders == 30


def test_rng_streams_differ_by_key():
    reg = RngRegistry(9)
    a = reg.stream("alpha").random()
    b = reg.stream("beta").random()
    assert a != b
    # Same key returns the same cached stream (so a second draw advances it).
    assert reg.stream("alpha") is reg.stream("alpha")
