"""A schema-constrained LLM strategist with an offline fallback.

The strategist proposes the next attack genome. It emits only schema-validated
genome parameters, and every prompt, response, and refusal is written to an audit
log. By default it runs a deterministic template-based planner, so the demo never
depends on a network call or an API key. A real language model can be injected
(see :mod:`hydraloop.red.llm`); its output is handled in three tiers:

1. **Strict** - a complete, valid genome is accepted verbatim.
2. **Repair** - a partial or slightly-out-of-bounds proposal is merged onto the
   parent and clamped to the DSL's hard bounds, then validated. This lets small
   local models steer the search without having to emit a perfect object.
3. **Refuse** - anything still invalid is logged as a refusal and the
   deterministic planner is used instead.

The model can therefore strengthen the search when present, but can never push an
invalid or out-of-policy genome through: the constrained genome is the guardrail.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .dsl.genome import Genome, GenomeValidationError, genome_from_dict
from .dsl.mutate import mutate
from .dsl.spec import GENE_SPEC
from .llm import extract_json

LLMClient = Callable[[str], str]


@dataclass
class AuditEntry:
    prompt: str
    response: str
    accepted: bool
    reason: str
    genome_id: str = ""
    family: str = ""


def _bounds_hint() -> str:
    """A compact, human-readable summary of the numeric gene bounds for prompts."""
    lines = []
    for group, fields in GENE_SPEC.items():
        parts = []
        for name, spec in fields.items():
            if spec.kind in {"float", "int"}:
                parts.append(f"{name} in [{spec.lo}, {spec.hi}]")
            elif spec.kind == "categorical":
                parts.append(f"{name} one of {list(spec.options or ())}")
        if parts:
            lines.append(f"- {group}: " + "; ".join(parts))
    return "\n".join(lines)


def _clamp_scalar(spec, value: Any) -> Any:
    if spec.kind == "float":
        try:
            return float(min(max(float(value), spec.lo), spec.hi))
        except (TypeError, ValueError):
            return None
    if spec.kind == "int":
        try:
            return int(min(max(int(round(float(value))), int(spec.lo)), int(spec.hi)))
        except (TypeError, ValueError):
            return None
    if spec.kind == "bool":
        return bool(value) if isinstance(value, bool) else None
    if spec.kind == "categorical":
        return value if value in (spec.options or ()) else None
    return None


def _apply_overlay(parent: Genome, overlay: dict[str, Any]) -> Genome:
    """Merge an LLM overlay of scalar/categorical genes onto the parent, clamped.

    Unknown groups/fields are ignored, numeric values are clamped to the DSL
    bounds, categoricals must be in-set, and the channel-mix simplex is
    renormalised. The result is guaranteed to be a structurally valid genome for
    the fields we touch; :meth:`Genome.validate` is the final gate.
    """
    genes = copy.deepcopy(parent.genes)
    for group, block in overlay.items():
        if group not in GENE_SPEC or not isinstance(block, dict):
            continue
        for name, raw in block.items():
            spec = GENE_SPEC[group].get(name)
            if spec is None:
                continue
            if spec.kind == "simplex" and isinstance(raw, dict):
                weights = {m: float(raw[m]) for m in (spec.members or ()) if m in raw and raw[m] >= 0}
                total = sum(weights.values())
                if len(weights) == len(spec.members or ()) and total > 0:
                    genes[group][name] = {m: w / total for m, w in weights.items()}
                continue
            clamped = _clamp_scalar(spec, raw)
            if clamped is not None:
                genes[group][name] = clamped
    return Genome(
        family=parent.family,
        genes=genes,
        attack_id=parent.attack_id,
        parent_id=parent.genome_id,
        label=f"{parent.attack_id or 'g'}.llm",
    )


@dataclass
class Strategist:
    rng: np.random.Generator
    llm: LLMClient | None = None
    audit_log: list[AuditEntry] = field(default_factory=list)

    def _prompt(self, parent: Genome, context: dict) -> str:
        return (
            "You are a red-team strategist in a synthetic, sandboxed payment-fraud "
            "lab. Propose the next attack as GENOME PARAMETERS ONLY - never any "
            "prose, credentials, messages, or step-by-step instructions.\n\n"
            "Return a JSON object with the same gene groups as the parent, nudging "
            "a few numeric values to make the attack settle more value while evading "
            "detection. Keep every value within these bounds:\n"
            f"{_bounds_hint()}\n\n"
            "channel_mix.weights must be three non-negative numbers for "
            "[a2a, wallet, card_not_present]. Output JSON only.\n\n"
            f"PARENT:\n{json.dumps(parent.to_dict(), sort_keys=True)}\n\n"
            f"CONTEXT:\n{json.dumps(context, sort_keys=True)}"
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
                AuditEntry(prompt, child.genome_id, True, "offline template planner",
                           child.genome_id, child.family)
            )
            return child

        raw = self.llm(prompt)
        cleaned = extract_json(raw)

        # Tier 1: a complete, valid genome is accepted verbatim.
        try:
            child = genome_from_dict(json.loads(cleaned))
            child.validate()
            self.audit_log.append(
                AuditEntry(prompt, raw, True, "llm output validated", child.genome_id, child.family)
            )
            return child
        except (json.JSONDecodeError, GenomeValidationError, KeyError, TypeError):
            pass

        # Tier 2: repair a partial/out-of-bounds proposal by clamping onto parent.
        try:
            data = json.loads(cleaned)
            overlay = data.get("genes", data) if isinstance(data, dict) else {}
            child = _apply_overlay(parent, overlay)
            child.validate()
            self.audit_log.append(
                AuditEntry(prompt, raw, True, "llm output repaired (clamped to bounds)",
                           child.genome_id, child.family)
            )
            return child
        except (json.JSONDecodeError, GenomeValidationError, KeyError, TypeError, AttributeError) as exc:
            self.audit_log.append(AuditEntry(prompt, raw, False, f"refused invalid output: {exc}"))
            return self._template_child(parent)

    def accepted(self) -> list[AuditEntry]:
        return [e for e in self.audit_log if e.accepted]

    def refusals(self) -> list[AuditEntry]:
        return [e for e in self.audit_log if not e.accepted]
