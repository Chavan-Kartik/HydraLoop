"""Tests for LLM client construction and the failure guard.

The offline guarantee is the property worth protecting here: an unconfigured or
misconfigured environment must yield no client at all, so Identify falls back to
the deterministic mapper instead of hanging on a provider that will not answer.
"""

from __future__ import annotations

from hydraloop.red.llm import (
    GuardedClient,
    OllamaClient,
    OpenAICompatClient,
    client_from_env,
    make_llm_client,
)

_ENV_KEYS = [
    "HYDRALOOP_LLM_PROVIDER",
    "HYDRALOOP_LLM_MODEL",
    "HYDRALOOP_LLM_BASE_URL",
    "HYDRALOOP_LLM_API_KEY",
    "HYDRALOOP_LLM_TIMEOUT",
]


def _clear_env(monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_unconfigured_environment_yields_no_client(monkeypatch):
    _clear_env(monkeypatch)
    assert client_from_env() is None


def test_hosted_provider_without_a_key_yields_no_client(monkeypatch):
    """A key-less hosted provider must not produce a client that always fails."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "openai")
    assert client_from_env() is None
    assert make_llm_client("openai", "m", base_url="https://x/v1", api_key="") is None


def test_unknown_provider_preserves_the_offline_default(monkeypatch):
    """A typo must not silently enable, or silently break, the request path."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "opeanai")
    monkeypatch.setenv("HYDRALOOP_LLM_API_KEY", "k")
    assert client_from_env() is None


def test_hosted_provider_with_a_key_is_guarded_and_configured(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "openai")
    monkeypatch.setenv("HYDRALOOP_LLM_API_KEY", "k")
    monkeypatch.setenv("HYDRALOOP_LLM_BASE_URL", "https://api.example/v1")
    monkeypatch.setenv("HYDRALOOP_LLM_MODEL", "some-model")
    monkeypatch.setenv("HYDRALOOP_LLM_TIMEOUT", "4.5")

    client = client_from_env()
    assert isinstance(client, GuardedClient)
    inner = client.inner
    assert isinstance(inner, OpenAICompatClient)
    assert inner.model == "some-model"
    assert inner.base_url == "https://api.example/v1"
    assert inner.timeout == 4.5


def test_unparseable_timeout_falls_back_to_a_sane_default(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "openai")
    monkeypatch.setenv("HYDRALOOP_LLM_API_KEY", "k")
    monkeypatch.setenv("HYDRALOOP_LLM_TIMEOUT", "soon")

    client = client_from_env()
    assert isinstance(client, GuardedClient)
    assert client.inner.timeout == 10.0


def test_ollama_stays_available_for_local_use(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "ollama")
    client = client_from_env()
    assert isinstance(client, GuardedClient)
    assert isinstance(client.inner, OllamaClient)


def test_guard_stops_calling_a_dead_provider():
    """After the breaker trips, the inner client must not be invoked again."""
    calls = []

    def always_fails(prompt: str) -> str:
        calls.append(prompt)
        return ""

    guard = GuardedClient(inner=always_fails, max_failures=3)
    for _ in range(10):
        assert guard("prompt") == ""

    assert len(calls) == 3, "guard kept paying for a provider that never answers"
    assert guard.tripped


def test_guard_resets_after_a_success():
    """A transient failure must not permanently disable a working provider."""
    replies = ["", "", '{"family": "card_testing"}', "", ""]
    seen = iter(replies)

    guard = GuardedClient(inner=lambda _p: next(seen), max_failures=3)
    outs = [guard("p") for _ in range(5)]

    assert outs[2] == '{"family": "card_testing"}'
    assert not guard.tripped, "one success should have cleared the failure count"


def test_a_key_less_hosted_client_short_circuits_without_a_network_call():
    client = OpenAICompatClient(model="m", api_key="", base_url="https://api.example/v1")
    assert client.available() is False
    assert client("prompt") == ""
