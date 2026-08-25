"""Tests for the offline-first LLM bridge."""

from __future__ import annotations

from hydraloop.red.llm import OllamaClient, extract_json, make_llm_client


def test_extract_json_pulls_balanced_object_from_prose():
    text = 'Sure! Here is the genome:\n```json\n{"family": "card_testing", "n": 1}\n``` done'
    assert extract_json(text) == '{"family": "card_testing", "n": 1}'


def test_extract_json_handles_nested_and_strings():
    text = 'noise {"a": {"b": 1}, "s": "with } brace"} trailing'
    assert extract_json(text) == '{"a": {"b": 1}, "s": "with } brace"}'


def test_extract_json_returns_empty_when_no_object():
    assert extract_json("this is not json") == ""


def test_make_llm_client_defaults_to_offline():
    assert make_llm_client("none", "x") is None
    assert make_llm_client("", "x") is None
    # Unknown providers must not silently enable anything.
    assert make_llm_client("definitely-not-a-provider", "x") is None


def test_make_llm_client_builds_ollama():
    client = make_llm_client("ollama", "llama3.2")
    assert isinstance(client, OllamaClient)


def test_ollama_client_is_defensive_when_unreachable():
    # Point at a dead port: available() is False and calls return "" (a refusal),
    # never an exception, so the strategist can always fall back.
    client = OllamaClient(model="x", base_url="http://127.0.0.1:9", timeout=1.0)
    assert client.available() is False
    assert client("any prompt") == ""
