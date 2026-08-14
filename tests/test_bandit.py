import numpy as np

from hydraloop.red.bandit import ThompsonSampler, optimise_strategy


def test_thompson_converges_to_best_arm():
    rng = np.random.default_rng(1)
    true_means = [0.1, 0.5, 0.9]
    sampler = ThompsonSampler(n_arms=3, rng=rng)
    pulls = [0, 0, 0]
    for _ in range(400):
        a = sampler.select()
        sampler.update(a, rng.normal(true_means[a], 0.1))
        pulls[a] += 1
    assert sampler.best_arm() == 2
    assert pulls[2] == max(pulls)  # it exploits the best arm most


def test_optimise_strategy_returns_history():
    rng = np.random.default_rng(2)
    arms = ["a", "b", "c"]
    rewards = {"a": 0.2, "b": 0.8, "c": 0.4}
    best, history = optimise_strategy(arms, lambda g: rewards[g], rounds=200, rng=rng)
    assert best == 1
    assert len(history) == 200
