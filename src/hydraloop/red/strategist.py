"""An optional, schema-constrained LLM strategist with an offline fallback.

The strategist proposes the next attack genome. It emits only schema-validated
genome JSON, and every prompt, response, and refusal is written to an audit log.
By default it runs a deterministic template-based planner, so the demo never
depends on a network call or an API key. An external model can be injected, but
any output that fails schema validation is refused and the fallback is used
instead -- the model can never push an invalid or out-of-policy genome through.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .dsl.genome import Genome, GenomeValidationError, genome_from_dict
from .dsl.mutate import mutate

LLMClient = Callable[[str], str]


@dataclass
class AuditEntry:
    prompt: str
    response: str
    accepted: bool
    reason: str


@dataclass
class Strategist:
    rng: np.random.Generator
    llm: LLMClient | None = None
    audit_log: list[AuditEntry] = field(default_factory=list)

    def _prompt(self, parent: Genome, context: dict) -> str:
        return json.dumps(
            {
                "instruction": "Propose one schema-valid attack genome as JSON.",
                "parent": parent.to_dict(),
                "context": context,
            },
            sort_keys=True,
        )

    def _template_child(self, parent: Genome) -> Genome:
        # Deterministic offline planner: a bounded mutation of the parent, which
        # is valid by construction because mutation clamps to gene bounds.
        return mutate(parent, self.rng, rate=0.3)

    def propose(self, parent: Genome, context: dict | None = None) -> Genome:
        context = context or {}
        prompt = self._prompt(parent, context)

        if self.llm is None:
            child = self._template_child(parent)
            self.audit_log.append(
                AuditEntry(prompt, child.genome_id, True, "offline template planner")
            )
            return child

        response = self.llm(prompt)
        try:
            data = json.loads(response)
            child = genome_from_dict(data)
            child.validate()
            self.audit_log.append(AuditEntry(prompt, response, True, "llm output validated"))
            return child
        except (json.JSONDecodeError, GenomeValidationError, KeyError, TypeError) as exc:
            self.audit_log.append(
                AuditEntry(prompt, response, False, f"refused invalid output: {exc}")
            )
            return self._template_child(parent)

    def refusals(self) -> list[AuditEntry]:
        return [e for e in self.audit_log if not e.accepted]
