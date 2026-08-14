import copy

import pytest

from hydraloop.red.dsl.genome import (
    GenomeValidationError,
    canonical_json,
    default_genome,
    genome_from_dict,
)


def test_default_genome_is_valid():
    default_genome().validate()


def test_hash_stable_under_reorder():
    g = default_genome(attack_id="AF-07")
    d = g.to_dict()
    # Reorder every dict key at every level; identity must be unchanged.
    reordered = {k: d[k] for k in reversed(list(d))}
    reordered["genes"] = {k: d["genes"][k] for k in reversed(list(d["genes"]))}
    g2 = genome_from_dict(reordered)
    assert g.genome_id == g2.genome_id


def test_hash_ignores_label_and_parent():
    g1 = default_genome(attack_id="AF-07")
    d = g1.to_dict()
    d["parent_id"] = "some-parent"
    d["label"] = "AF-07.g3.v1"
    g2 = genome_from_dict(d)
    assert g1.genome_id == g2.genome_id


def test_hash_changes_with_genes():
    g1 = default_genome(attack_id="AF-07")
    d = copy.deepcopy(g1.to_dict())
    d["genes"]["network_topology"]["mule_fanout"] = 7
    g2 = genome_from_dict(d)
    assert g1.genome_id != g2.genome_id


def test_out_of_range_rejected():
    d = default_genome().to_dict()
    d["genes"]["network_topology"]["mule_fanout"] = 999
    with pytest.raises(GenomeValidationError):
        genome_from_dict(d)


def test_unknown_family_rejected():
    d = default_genome().to_dict()
    d["family"] = "not_a_family"
    with pytest.raises(GenomeValidationError):
        genome_from_dict(d)


def test_simplex_must_sum_to_one():
    d = default_genome().to_dict()
    d["genes"]["channel_mix"]["weights"] = {"a2a": 0.5, "wallet": 0.2, "card_not_present": 0.1}
    with pytest.raises(GenomeValidationError):
        genome_from_dict(d)


def test_ladder_must_be_non_decreasing():
    d = default_genome().to_dict()
    d["genes"]["amount_policy"]["steps"] = [0.5, 0.3, 0.1]
    with pytest.raises(GenomeValidationError):
        genome_from_dict(d)


def test_bool_not_accepted_as_int():
    d = default_genome().to_dict()
    d["genes"]["network_topology"]["mule_fanout"] = True
    with pytest.raises(GenomeValidationError):
        genome_from_dict(d)


def test_canonical_json_rounds_floats():
    a = canonical_json({"x": 0.1 + 0.2})
    b = canonical_json({"x": 0.3})
    assert a == b
