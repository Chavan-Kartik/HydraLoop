from hydraloop.evaluation.sensitivity import Assumption, plot_tornado, sweep


def test_pm50_range():
    a = Assumption.pm50("w", 10.0)
    assert a.low == 5.0 and a.high == 15.0


def test_sweep_ranks_by_swing():
    # metric depends strongly on 'a', weakly on 'b'.
    def metric(p):
        return 100.0 * p["a"] + 1.0 * p["b"]

    base = {"a": 1.0, "b": 1.0}
    rows = sweep(metric, [Assumption.pm50("a", 1.0), Assumption.pm50("b", 1.0)], base)
    assert rows[0].name == "a"  # largest swing first
    assert rows[0].swing > rows[1].swing


def test_tornado_plot_written(tmp_path):
    def metric(p):
        return p["a"] + p["b"]

    base = {"a": 1.0, "b": 2.0}
    rows = sweep(metric, [Assumption.pm50("a", 1.0), Assumption.pm50("b", 2.0)], base)
    path = plot_tornado(rows, tmp_path / "t.png")
    assert path.exists() and path.stat().st_size > 0
