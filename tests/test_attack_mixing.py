from hydraloop.red.dsl import genome_from_template
from hydraloop.red.mixer import build_attack_specs
from hydraloop.twin.population import SECONDS_PER_DAY
from hydraloop.twin.run import build_engine, legit_session_specs


def test_fraud_and_legit_interleave(small_config):
    engine, registry = build_engine(small_config)
    horizon_s = small_config.simulation.horizon_days * SECONDS_PER_DAY
    legit = legit_session_specs(small_config, engine, registry, 200)
    genome = genome_from_template("social_engineering", "AF-09", {})
    fraud, ledger = build_attack_specs(engine, registry, [genome], 30, horizon_s)
    assert fraud
    assert ledger.balances()

    result = engine.simulate(legit + fraud)
    tx = result.transactions
    fraud_ts = [t["ts"] for t in tx if t["is_fraud"]]
    legit_ts = [t["ts"] for t in tx if not t["is_fraud"]]
    # Interference: fraud timestamps fall inside the legit time range, not after it.
    assert min(legit_ts) <= min(fraud_ts)
    assert max(fraud_ts) <= max(legit_ts) + 1e6
    assert any(t["is_fraud"] for t in tx)
