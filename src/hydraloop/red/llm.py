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
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

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
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return str(body.get("response", ""))
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            return ""


def make_llm_client(provider: str, model: str, base_url: str = "http://localhost:11434") -> LLMClient | None:
    """Build an LLM client for a provider name, or ``None`` for the offline default.

    ``provider`` of ``none``/``off``/``""`` returns ``None`` (deterministic
    planner). ``ollama`` returns a local client. Unknown providers return ``None``
    so a typo can never silently disable the offline guarantee.
    """
    provider = (provider or "none").strip().lower()
    if provider in {"", "none", "off", "offline"}:
        return None
    if provider == "ollama":
        return OllamaClient(model=model, base_url=base_url)
    return None


__all__ = ["LLMClient", "OllamaClient", "extract_json", "make_llm_client"]
