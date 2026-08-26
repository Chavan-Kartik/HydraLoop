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
        # Ask for a small numeric overlay, not a full attack genome dump. Hosted
        # safety filters refuse when the parent JSON names families like
        # ``synthetic_identity`` or genes like ``mule_fanout``, and return prose
        # or an empty completion that then looks like a dead provider. The repair
        # tier already merges a partial overlay onto the parent and clamps it.
        genes = parent.genes
        timing = genes.get("timing_policy") or {}
        amount = genes.get("amount_policy") or {}
        channel = (genes.get("channel_mix") or {}).get("weights") or {}
        snapshot = {
            "inter_txn_delay_mu": timing.get("inter_txn_delay_mu"),
            "dwell_before_cashout_h": timing.get("dwell_before_cashout_h"),
            "max_fraction": amount.get("max_fraction"),
            "channel_weights": {
                "a2a": channel.get("a2a"),
                "wallet": channel.get("wallet"),
                "card_not_present": channel.get("card_not_present"),
            },
            "episode": context.get("generation"),
            "prior_settled_value": context.get("prior_settled_value"),
        }
        return (
            "You tune numeric knobs for a closed-lab payment simulator. "
            "Reply with JSON ONLY and no other text. Never include messages, "
            "credentials, or instructions.\n\n"
            "Return an object shaped like:\n"
            '{"timing_policy": {"inter_txn_delay_mu": <0..12>, '
            '"dwell_before_cashout_h": <0..168>}, '
            '"amount_policy": {"max_fraction": <0..1>}, '
            '"channel_mix": {"weights": {"a2a": <n>, "wallet": <n>, '
            '"card_not_present": <n>}}}\n\n'
            "Nudge one or two values from CURRENT. If prior_settled_value is "
            "low or zero, prefer a slightly smaller inter_txn_delay_mu or a "
            "slightly larger max_fraction. channel weights must be non-negative "
            "and will be renormalised.\n\n"
            f"CURRENT:\n{json.dumps(snapshot, sort_keys=True)}"
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


def audit_report(
    strategist: Strategist, proposals: list[Genome], client: LLMClient | None
) -> dict[str, Any]:
    """Project the audit log into the record the Strategist screen reads.

    Shared by both drivers that run a strategist so the screen means the same
    thing whichever produced the run. ``llm_authored`` counts only proposals a
    model actually authored, which is why it is derived from the audit reasons
    rather than from whether a client was configured.
    """
    from .dsl.render import render_brief
    from .llm import describe_client

    entries = [
        {"accepted": e.accepted, "reason": e.reason, "genome_id": e.genome_id, "family": e.family}
        for e in strategist.audit_log
    ]
    # Join on genome_id, never on position: the audit log accumulates across all
    # generations and also records refusals, which carry no genome, so zipping it
    # against one generation's proposals would attach the wrong reason to a genome.
    by_id = {g.genome_id: g for g in proposals}
    samples = []
    for entry in strategist.audit_log:
        if not (entry.accepted and "llm" in entry.reason):
            continue
        genome = by_id.get(entry.genome_id)
        if genome is None:
            continue
        samples.append(
            {
                "genome_id": genome.genome_id,
                "family": genome.family,
                "reason": entry.reason,
                "brief": render_brief(genome),
            }
        )
    return {
        **describe_client(client),
        "proposals": len(strategist.audit_log),
        "accepted": len(strategist.accepted()),
        "refused": len(strategist.refusals()),
        "llm_authored": len(samples),
        "samples": samples[:6],
        "entries": entries,
    }
