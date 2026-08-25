from collections import Counter

from hydraloop.catalog import load_catalog
from hydraloop.red.dsl import FAMILIES, genome_from_template, render_brief


def test_catalog_has_28_scenarios():
    scenarios = load_catalog()
    assert len(scenarios) == 28


def test_all_families_have_four_scenarios():
    scenarios = load_catalog()
    counts = Counter(s.family for s in scenarios)
    assert set(counts) == set(FAMILIES)
    assert all(counts[f] == 4 for f in FAMILIES)


def test_at_least_six_evolvable():
    scenarios = load_catalog()
    evolvable = [s for s in scenarios if s.evolvable]
    assert len(evolvable) >= 6


def test_evolvable_templates_build_valid_genomes():
    scenarios = load_catalog()
    for s in scenarios:
        if not s.evolvable:
            continue
        g = genome_from_template(s.family, s.attack_id, s.genome_template)
        g.validate()
        assert g.family == s.family


def test_briefs_are_readable():
    scenarios = load_catalog()
    evolvable = [s for s in scenarios if s.evolvable]
    g = genome_from_template(evolvable[0].family, evolvable[0].attack_id, evolvable[0].genome_template)
    brief = render_brief(g)
    assert len(brief) > 80
    assert evolvable[0].attack_id in brief


def test_evolvable_covers_all_families():
    scenarios = load_catalog()
    evolvable_families = {s.family for s in scenarios if s.evolvable}
    assert evolvable_families == set(FAMILIES)
