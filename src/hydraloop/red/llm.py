"""A local, offline-first LLM bridge for the red team.

The whole point of the challenge is *GenAI*-powered fraud, so the red team can be
driven by a real language model. To keep the lab runnable at a venue with no
network and no API key, the default provider is Ollama on ``localhost`` and every
call is defensive: any failure (model not running, timeout, malformed output)
returns an empty string, which the schema-validating strategist then refuses and
falls back to its deterministic planner. The model can therefore *strengthen* the
search when present but can never break the run or push an out-of-policy genome.

Nothing here ever emits attack recipes: the model is only ever asked for bounded
genome parameters as JSON, and its output is schema-validated and clamped before
it can touch the twin.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache

LLMClient = Callable[[str], str]


def extract_json(text: str) -> str:
    """Return the first balanced ``{...}`` block in *text*, or ``""``.

    Small local models love to wrap JSON in prose or ``` fences; we pull out the
    first balanced object so the strategist can parse it. Returns an empty string
    when there is no balanced object, which downstream treats as a refusal.
    """
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    """Pull the provider's own explanation out of an error response.

    These providers put the useful part in the body, not the status line: a
    retired model name and a revoked key both arrive as a bare ``400`` whose body
    says which one it was. Falls back to the status reason when the body is not
    the usual ``{"error": {"message": ...}}`` shape.
    """
    try:
        raw = exc.read().decode("utf-8", "replace")
    except OSError:
        raw = ""
    # Worst case, hand back the raw body: still far more use than the status code.
    fallback = raw.strip()[:300] or exc.reason or "no detail given"
    try:
        body = json.loads(raw)
    except ValueError:
        return fallback
    # Gemini's compatibility endpoint wraps the error object in a one-element
    # array; Groq, OpenRouter and OpenAI itself return it bare.
    if isinstance(body, list):
        body = next((item for item in body if isinstance(item, dict)), None)
    if not isinstance(body, dict):
        return fallback
    err = body.get("error", body)
    if isinstance(err, dict):
        return str(err.get("message") or err.get("status") or err)[:300]
    return str(err)[:300] or fallback


@dataclass
class OllamaClient:
    """Callable LLM client backed by a local Ollama server.

    Instances are ``Callable[[str], str]`` so they slot straight into the
    strategist. Failures are swallowed and returned as ``""`` so the caller's
    schema validation refuses cleanly and falls back.
    """

    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    timeout: float = 30.0
    system: str | None = None
    last_error: str = field(default="", init=False)

    def available(self) -> bool:
        """Cheap liveness check: is an Ollama server answering locally?"""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def __call__(self, prompt: str) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
            "format": "json",
        }
        if self.system:
            payload["system"] = self.system
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        self.last_error = ""
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return str(body.get("response", ""))
        except urllib.error.HTTPError as exc:
            self.last_error = f"ollama returned HTTP {exc.code}: {_http_error_detail(exc)}"
        except (urllib.error.URLError, OSError) as exc:
            self.last_error = f"no ollama server at {self.base_url}: {exc}"
        except ValueError as exc:
            self.last_error = f"could not read ollama's reply: {exc!r}"
        return ""


@dataclass
class OpenAICompatClient:
    """Callable LLM client for any OpenAI-compatible ``/chat/completions`` endpoint.

    Ollama solves the offline case but only ever listens on localhost, so it
    cannot serve a deployed backend. This covers the hosted case with one client,
    because Groq, OpenRouter, Together and Gemini's compatibility endpoint all
    speak the same dialect and differ only in base URL and model name.

    Deliberately no ``response_format`` is sent. Support for it varies between
    these providers, and a provider that rejects the field would fail the whole
    call, which degrades to the keyword mapper silently. Asking for JSON in the
    prompt and recovering it with :func:`extract_json` is portable instead.

    ``reasoning_effort`` follows the same rule and defaults to unset. It matters
    for reasoning models, which spend thinking tokens before their first output
    byte and can exceed the timeout on a prompt this small, but sending it to a
    host that does not know the field fails the request outright.

    Like :class:`OllamaClient`, every failure returns ``""`` so the caller's
    schema validation refuses cleanly and falls back. The reason is kept in
    :attr:`last_error` rather than discarded, because silent degradation is
    correct for a visitor and useless for whoever is holding the key.
    """

    model: str
    api_key: str
    base_url: str
    temperature: float = 0.2
    timeout: float = 10.0
    reasoning_effort: str = ""
    last_error: str = field(default="", init=False)

    def available(self) -> bool:
        """True when a key is configured. Deliberately makes no network call."""
        return bool(self.api_key)

    # Below this, a "key" is a fragment that occurs in ordinary words, and
    # replacing it corrupts the message it is meant to be protecting.
    _MIN_REDACTABLE = 8

    def _redact(self, message: str) -> str:
        """Never let the key travel with the reason it failed."""
        if len(self.api_key) < self._MIN_REDACTABLE:
            return message
        return message.replace(self.api_key, "***")

    def __call__(self, prompt: str) -> str:
        self.last_error = ""
        if not self.api_key:
            self.last_error = "no API key is set"
            return ""
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        # Only sent when asked for, because providers disagree about it: Gemini's
        # reasoning models need it to answer promptly, while a host that does not
        # recognise the field rejects the whole request.
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            choice = body["choices"][0]
            message = choice.get("message") or {}
            content = message.get("content")
            if content is None or content == "":
                finish = choice.get("finish_reason") or body.get("error") or "empty content"
                self.last_error = self._redact(
                    f"provider returned no content for model '{self.model}' "
                    f"(finish_reason={finish!r})"
                )
                return ""
            return str(content)
        except urllib.error.HTTPError as exc:
            self.last_error = self._redact(
                f"provider refused model '{self.model}' with HTTP {exc.code}: "
                f"{_http_error_detail(exc)}"
            )
        except (urllib.error.URLError, OSError) as exc:
            self.last_error = self._redact(f"could not reach {self.base_url}: {exc}")
        except (ValueError, KeyError, IndexError) as exc:
            self.last_error = f"could not read the provider's reply: {exc!r}"
        return ""


@dataclass
class GuardedClient:
    """Stop paying for a provider that has stopped answering.

    Without this, a wrong key or a dead endpoint costs every single request the
    full timeout before falling back, which is worse for a visitor than not
    configuring a model at all. After ``max_failures`` consecutive empty
    responses this returns ``""`` immediately; one success resets the count.

    The failure count is mutated under a lock because one cached instance is
    shared by the request handlers and by co-evolution runs on the background
    pool, so concurrent callers would otherwise race on it.
    """

    inner: LLMClient
    max_failures: int = 3
    _failures: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __call__(self, prompt: str) -> str:
        with self._lock:
            if self._failures >= self.max_failures:
                return ""
        out = self.inner(prompt)
        with self._lock:
            self._failures = 0 if out else self._failures + 1
        return out

    @property
    def tripped(self) -> bool:
        return self._failures >= self.max_failures

    @property
    def last_error(self) -> str:
        """Why the wrapped client last came back empty, if it said.

        Delegated so callers can hold the guard without having to know what it
        wraps. Once tripped the inner client is no longer called, so the stored
        reason is the one that caused the breaker to open.
        """
        reason = str(getattr(self.inner, "last_error", ""))
        if self.tripped:
            return (
                f"not calling the provider after {self._failures} consecutive "
                f"failures; last reason: {reason or 'unknown'}"
            )
        return reason


def make_llm_client(
    provider: str,
    model: str,
    base_url: str = "http://localhost:11434",
    api_key: str = "",
) -> LLMClient | None:
    """Build an LLM client for a provider name, or ``None`` for the offline default.

    ``provider`` of ``none``/``off``/``""`` returns ``None`` (deterministic
    planner). ``ollama`` returns a local client, ``openai`` any OpenAI-compatible
    host. Unknown providers return ``None`` so a typo can never silently disable
    the offline guarantee.
    """
    provider = (provider or "none").strip().lower()
    if provider in {"", "none", "off", "offline"}:
        return None
    if provider == "ollama":
        return OllamaClient(model=model, base_url=base_url)
    if provider in {"openai", "openai-compat", "groq", "openrouter"}:
        if not api_key:
            return None
        return OpenAICompatClient(model=model, api_key=api_key, base_url=base_url)
    return None


def client_from_env() -> LLMClient | None:
    """Build the request-path LLM client from the environment, or ``None``.

    Reading configuration here rather than at the call sites keeps the API
    modules free of provider detail. Absent or unparseable configuration yields
    ``None``, which preserves the offline guarantee: no environment variables set
    means the deterministic keyword mapper, exactly as before.
    """
    provider = os.environ.get("HYDRALOOP_LLM_PROVIDER", "none")
    base_url = os.environ.get("HYDRALOOP_LLM_BASE_URL", "http://localhost:11434")
    model = os.environ.get("HYDRALOOP_LLM_MODEL", "llama3.2")
    api_key = os.environ.get("HYDRALOOP_LLM_API_KEY", "")

    client = make_llm_client(provider, model, base_url=base_url, api_key=api_key)
    if client is None:
        return None

    try:
        timeout = float(os.environ.get("HYDRALOOP_LLM_TIMEOUT", "10"))
    except ValueError:
        timeout = 10.0
    if isinstance(client, OpenAICompatClient | OllamaClient):
        client.timeout = timeout
    if isinstance(client, OpenAICompatClient):
        client.reasoning_effort = os.environ.get("HYDRALOOP_LLM_REASONING_EFFORT", "").strip()

    return GuardedClient(inner=client)


def describe_client(client: LLMClient | None) -> dict[str, object]:
    """What is actually wired up, for audit records and the health endpoint.

    Derived from the object rather than from the configuration that was asked
    for, because the two can disagree: a hosted provider named without a key
    builds no client at all, and reporting the requested name in that case would
    claim a model was driving a run that the deterministic planner drove.
    """
    if client is None:
        return {"provider": "none", "model": None, "available": False}
    inner = getattr(client, "inner", client)
    if isinstance(inner, OllamaClient):
        return {"provider": "ollama", "model": inner.model, "available": inner.available()}
    if isinstance(inner, OpenAICompatClient):
        return {
            "provider": "openai-compatible",
            "model": inner.model,
            "available": inner.available(),
        }
    return {"provider": "custom", "model": getattr(inner, "model", None), "available": True}


@lru_cache(maxsize=1)
def request_path_client() -> LLMClient | None:
    """The single client shared by API request handlers.

    Cached on purpose. :class:`GuardedClient` counts consecutive failures, and a
    fresh instance per request would reset that count every time, so a dead
    provider would cost every visitor the full timeout forever. One instance for
    the process means the breaker trips once and stays tripped.
    """
    return client_from_env()


__all__ = [
    "GuardedClient",
    "LLMClient",
    "OllamaClient",
    "OpenAICompatClient",
    "client_from_env",
    "describe_client",
    "extract_json",
    "make_llm_client",
    "request_path_client",
]
