import json

import pytest

from hydraloop.loop.ledger import GENESIS, GenerationLedger


def test_chain_links_and_reconstructs(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = GenerationLedger(path)
    led.append({"generation": 1, "escape_rate": 1.0})
    led.append({"generation": 2, "escape_rate": 0.3})
    assert led.entries[0]["prev_hash"] == GENESIS
    assert led.entries[1]["prev_hash"] == led.entries[0]["entry_hash"]

    reloaded = GenerationLedger.load(path)  # verify() runs on load
    assert len(reloaded.entries) == 2
    assert reloaded.head_hash == led.head_hash


def test_tamper_is_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = GenerationLedger(path)
    led.append({"generation": 1, "escape_rate": 1.0})
    led.append({"generation": 2, "escape_rate": 0.3})

    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["payload"]["escape_rate"] = 0.0  # rewrite history
    lines[0] = json.dumps(first, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        GenerationLedger.load(path)
