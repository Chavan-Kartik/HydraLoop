"""Tests for LLM client construction and the failure guard.

The offline guarantee is the property worth protecting here: an unconfigured or
misconfigured environment must yield no client at all, so Identify falls back to
the deterministic mapper instead of hanging on a provider that will not answer.
"""

from __future__ import annotations

import email.message
import io
import json
import urllib.error

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
    "HYDRALOOP_LLM_REASONING_EFFORT",
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
    assert "no API key" in client.last_error


def _http_error(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.example/v1/chat/completions",
        code=code,
        msg="Bad Request",
        hdrs=email.message.Message(),
        fp=io.BytesIO(body.encode("utf-8")),
    )


def _raising(exc: Exception):
    def _urlopen(*_args, **_kwargs):
        raise exc

    return _urlopen


def test_a_refused_request_records_the_providers_own_explanation(monkeypatch):
    """The body carries the reason; a bare status code cannot distinguish causes.

    A retired model name and a revoked key both arrive as HTTP 400, so discarding
    the body leaves no way to tell them apart.
    """
    body = '{"error": {"message": "models/nope is not found", "code": 400}}'
    monkeypatch.setattr("urllib.request.urlopen", _raising(_http_error(400, body)))

    client = OpenAICompatClient(model="nope", api_key="k", base_url="https://api.example/v1")
    assert client("prompt") == "", "a refused call must still degrade to the fallback"
    assert "400" in client.last_error
    assert "models/nope is not found" in client.last_error


def test_a_gemini_style_array_wrapped_error_is_still_readable(monkeypatch):
    """Gemini's compat endpoint returns ``[{"error": ...}]``, not a bare object.

    Verbatim from the live endpoint. Treating only the bare-object shape as valid
    surfaced the raw JSON instead of the sentence inside it.
    """
    body = (
        '[{\n  "error": {\n    "code": 400,\n'
        '    "message": "Please pass a valid API key",\n'
        '    "status": "INVALID_ARGUMENT"\n  }\n}\n]'
    )
    monkeypatch.setattr("urllib.request.urlopen", _raising(_http_error(400, body)))

    client = OpenAICompatClient(model="m", api_key="k", base_url="https://api.example/v1")
    assert client("prompt") == ""
    assert client.last_error.endswith("Please pass a valid API key")


def test_an_error_message_never_carries_the_api_key(monkeypatch):
    """Providers echo the offending key back; last_error can reach logs."""
    key = "sk-do-not-leak-this"
    body = f'{{"error": {{"message": "API key not valid: {key}"}}}}'
    monkeypatch.setattr("urllib.request.urlopen", _raising(_http_error(400, body)))

    client = OpenAICompatClient(model="m", api_key=key, base_url="https://api.example/v1")
    client("prompt")
    assert key not in client.last_error
    assert "***" in client.last_error


def test_an_unreachable_host_is_reported_rather_than_swallowed(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen", _raising(urllib.error.URLError("name resolution failed"))
    )

    client = OpenAICompatClient(model="m", api_key="k", base_url="https://api.example/v1")
    assert client("prompt") == ""
    assert "https://api.example/v1" in client.last_error


def test_a_malformed_reply_is_reported_rather_than_swallowed(monkeypatch):
    class _Resp:
        def read(self):
            return b'{"unexpected": "shape"}'

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: _Resp())

    client = OpenAICompatClient(model="m", api_key="k", base_url="https://api.example/v1")
    assert client("prompt") == ""
    assert client.last_error, "an unreadable reply left no diagnosis"


def test_llm_check_reports_the_offline_default_without_a_network_call(monkeypatch):
    """Unconfigured must read as deliberate, not as a broken model."""
    from typer.testing import CliRunner

    from hydraloop.cli import app

    _clear_env(monkeypatch)
    result = CliRunner().invoke(app, ["llm-check"])

    assert result.exit_code == 0
    assert "keyword mapper" in result.stdout


class _OkResponse:
    """Minimal stand-in for a successful chat completion."""

    def read(self):
        return b'{"choices": [{"message": {"content": "ok"}}]}'

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_reasoning_effort_is_sent_only_when_configured(monkeypatch):
    """Unset by default: a host that does not know the field rejects the request.

    Reasoning models need it to answer a short prompt inside the timeout, so it
    has to be sendable, but it cannot be sent unconditionally.
    """
    seen: dict = {}

    def _urlopen(req, **_kwargs):
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _OkResponse()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    client = OpenAICompatClient(model="m", api_key="k", base_url="https://api.example/v1")
    assert client("p") == "ok"
    assert "reasoning_effort" not in seen["body"]

    client.reasoning_effort = "minimal"
    client("p")
    assert seen["body"]["reasoning_effort"] == "minimal"


def test_reasoning_effort_is_read_from_the_environment(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("HYDRALOOP_LLM_PROVIDER", "openai")
    monkeypatch.setenv("HYDRALOOP_LLM_API_KEY", "k")
    monkeypatch.setenv("HYDRALOOP_LLM_REASONING_EFFORT", "minimal")

    client = client_from_env()
    assert isinstance(client, GuardedClient)
    assert client.inner.reasoning_effort == "minimal"


def test_the_guard_surfaces_the_inner_reason_and_says_when_it_gave_up():
    """Callers hold the guard, not the client, so the reason must pass through."""
    client = OpenAICompatClient(model="m", api_key="", base_url="https://api.example/v1")
    guard = GuardedClient(inner=client, max_failures=3)

    guard("p")
    assert "no API key" in guard.last_error
    assert "consecutive" not in guard.last_error, "reported giving up after one failure"

    guard("p")
    guard("p")
    assert guard.tripped
    assert "consecutive" in guard.last_error
    assert "no API key" in guard.last_error, "lost the reason the breaker opened"
