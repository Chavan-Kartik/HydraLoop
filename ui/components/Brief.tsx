"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { KeyRound, Shield, Sparkles } from "lucide-react";
import { getStrategist, latestRunId, Strategist } from "@/lib/api";
import { Badge, Card, SectionLabel } from "./ui";

const FALLBACK: Strategist["pipeline"] = [
  {
    verb: "Identify",
    title: "Emerging GenAI fraud, as behaviour",
    detail:
      "28 catalogued scenarios across 7 families, including agentic commerce. A writeup maps to a bounded genome, never a recipe.",
    href: "/threats",
  },
  {
    verb: "Generate",
    title: "Schema-constrained proposals, then the twin",
    detail:
      "The strategist only emits genome parameters. Invalid output is refused. The twin runs what survives against a live policy.",
    href: "/lineage",
  },
  {
    verb: "Defend",
    title: "Escapes become the next training set",
    detail:
      "The ensemble scores, the policy acts, immune memory retrains, and a gauntlet must pass before promotion.",
    href: "/investigations",
  },
];

export function VerbStrip() {
  const [steps, setSteps] = useState(FALLBACK);

  useEffect(() => {
    (async () => {
      try {
        const { runId } = await latestRunId();
        const { data } = await getStrategist(runId ?? "seed");
        if (data.pipeline?.length) setSteps(data.pipeline);
      } catch {
        /* keep fallback */
      }
    })();
  }, []);

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
      {steps.map((s, i) => (
        <Link key={s.verb} href={s.href} className="block">
          <Card className="h-full p-4 transition-shadow hover:shadow-raised">
            <div className="flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-full bg-accent-600 text-[11px] font-bold text-white">
                {i + 1}
              </span>
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-700">
                {s.verb}
              </span>
            </div>
            <div className="mt-2 text-sm font-bold text-ink">{s.title}</div>
            <p className="mt-1 text-xs leading-relaxed text-ink-faint">{s.detail}</p>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function StrategistBeat() {
  const [data, setData] = useState<Strategist | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { runId } = await latestRunId();
        const { data } = await getStrategist(runId ?? "seed");
        setData(data);
      } catch {
        setData(null);
      }
    })();
  }, []);

  const proposals = data?.proposals ?? 0;
  const accepted = data?.accepted ?? 0;
  const refused = data?.refused ?? 0;
  const llmAuthored = data?.llm_authored ?? 0;
  const modelReady = Boolean(data?.available);
  const modelName = data?.model ?? null;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionLabel>Red-team strategist (GenAI, constrained)</SectionLabel>
          <div className="mt-1 text-base font-bold text-ink">
            The attack never leaves the genome schema.
          </div>
        </div>
        <Badge tone="green">
          <KeyRound className="h-3 w-3" />
          {modelReady ? (modelName ?? "model configured") : "runs without an API key"}
        </Badge>
      </div>

      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-faint">
        Unconfigured, a deterministic planner proposes the next genome, so the demo runs
        offline. With a model configured, the strategist asks it for bounded numeric
        parameters only. Every proposal is schema-validated and clamped to the DSL&apos;s
        hard bounds, and anything still invalid is logged as a refusal instead of executed.
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Proposals" value={proposals} />
        <Stat label="Accepted" value={accepted} />
        <Stat label="Refused" value={refused} />
        <Stat
          label="LLM-authored"
          value={llmAuthored}
          hint={llmAuthored === 0 ? "planner" : (modelName ?? data?.provider ?? "model")}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-ink-faint">
        <span className="chip">
          <Sparkles className="h-3 w-3 text-accent-700" />
          {data?.default_mode ?? "constrained_planner"}
        </span>
        <span className="chip">
          <Shield className="h-3 w-3 text-accent-700" />
          {data?.guardrail ?? "schema-validated genome only"}
        </span>
        {data?.source && (
          <span className="chip">source {data.source}</span>
        )}
      </div>
    </Card>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="rounded border border-line bg-subtle/50 px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-ghost">{label}</div>
      <div className="font-mono text-xl font-bold tabular-nums text-ink">{value}</div>
      {hint && <div className="text-[10px] text-ink-ghost">{hint}</div>}
    </div>
  );
}
