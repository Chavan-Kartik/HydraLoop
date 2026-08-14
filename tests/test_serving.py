import time

from hydraloop.blue.serving import ScoringService


def test_normal_mode_not_degraded():
    svc = ScoringService(primary=lambda f: 0.3, latency_budget_ms=1000.0)
    res = svc.score({})
    assert res.prob == 0.3
    assert res.degraded is False


def test_degraded_mode_latches_and_uses_fallback():
    def slow(_features):
        time.sleep(0.02)  # 20ms, over the 1ms budget
        return 0.9

    svc = ScoringService(primary=slow, fallback=lambda f: 0.1, latency_budget_ms=1.0)
    first = svc.score({})
    assert first.degraded is True
    second = svc.score({})
    # Once degraded, the cheaper fallback scorer is used.
    assert second.prob == 0.1


def test_percentiles_reported():
    svc = ScoringService(primary=lambda f: 0.5, latency_budget_ms=1000.0)
    for _ in range(20):
        svc.score({})
    pct = svc.percentiles()
    assert pct["p99"] >= pct["p50"] >= 0.0
