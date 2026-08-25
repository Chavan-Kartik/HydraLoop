"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ScanSearch, AlertTriangle, CheckCircle2, GitCompareArrows } from "lucide-react";
import { getInvestigations, getLabLatest, InvestigationCase, latestRunId } from "@/lib/api";
import {
  Figure,
  ARROW,
  Badge,
  ErrorBox,
  Card,
  Loading,
  OfflineBadge,
  Panel,
  SectionLabel,
} from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

export function Investigations() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [selected, setSelected] = useState<InvestigationCase | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const lab = await getLabLatest();
        let cases: InvestigationCase[] = Array.isArray(lab?.cases) ? lab.cases : [];
        let offline = false;
        if (!cases.length) {
          const { runId } = await latestRunId();
          const inv = await getInvestigations(runId ?? "seed");
          cases = Array.isArray(inv.data.cases) ? inv.data.cases : [];
          offline = inv.offline;
        }
        if (!cases.length) {
          try {
            const cached = sessionStorage.getItem("hydraloop-lab-last");
            if (cached) {
              const parsed = JSON.parse(cached) as { cases?: InvestigationCase[] };
              cases = Array.isArray(parsed.cases) ? parsed.cases : [];
            }
          } catch {
            /* ignore */
          }
        }
        setCases(cases);
        setSelected(cases[0] ?? null);
        setOffline(offline);
        setStatus(cases.length ? "ready" : "empty");
      } catch (e) {
        setError((e as Error).message);
        setStatus("error");
      }
    })();
  }, []);

  if (status === "loading") return <Loading label="investigations" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (status === "empty") {
    return (
      <div className="rounded-md border border-dashed border-line bg-surface/50 p-10 text-center text-sm text-ink-faint">
        No flagged transactions yet.{" "}
        <Link href="/" className="font-semibold text-accent-700 underline">
          Run the lab
        </Link>{" "}
        first. The investigation pane fills from that live episode.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {offline && <OfflineBadge />}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title={`Flagged (${cases.length})`}>
          <ul className="scroll-thin max-h-[30rem] space-y-1.5 overflow-y-auto pr-1">
            {cases.map((c) => {
              const active = selected?.txn_id === c.txn_id;
              const hot = c.risk_score >= 0.5;
              return (
                <li key={c.txn_id}>
                  <button
                    onClick={() => setSelected(c)}
                    className={`flex w-full items-center justify-between gap-2 rounded border px-3 py-2 text-left transition-colors ${
                      active
                        ? "border-accent-200 bg-accent-50"
                        : "border-line bg-surface hover:border-accent-200"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className={`h-1.5 w-1.5 rounded-full ${hot ? "bg-red" : "bg-blue"}`} />
                      <span className="truncate font-mono text-xs text-ink-soft">{c.txn_id}</span>
                    </span>
                    <span className={`font-mono text-sm font-bold ${hot ? "text-red" : "text-blue"}`}>
                      {c.risk_score.toFixed(2)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>

        <div className="lg:col-span-2">{selected && <CaseDetail c={selected} />}</div>
      </div>
    </div>
  );
}

function CaseDetail({ c }: { c: InvestigationCase }) {
  const maxAbs = Math.max(...c.reason_codes.map((r) => Math.abs(r.contribution)), 1);
  const cf = c.counterfactual;
  const drop = cf ? cf.risk_before - cf.risk_after : 0;
  const hot = c.risk_score >= 0.5;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <span
            className={`grid h-12 w-12 place-items-center rounded-md ${hot ? "bg-red/10 text-red" : "bg-blue/10 text-blue"}`}
          >
            <ScanSearch className="h-6 w-6" />
          </span>
          <div>
            <div className="font-mono text-xs text-ink-ghost">{c.txn_id}</div>
            <div className={`font-mono text-4xl font-bold tabular-nums ${hot ? "text-red" : "text-blue"}`}>
              <Figure value={c.risk_score} format={(n) => n.toFixed(3)} />
            </div>
            <SectionLabel>risk score</SectionLabel>
          </div>
        </div>
        <Badge tone={c.is_fraud ? "red" : "green"}>
          {c.is_fraud ? <AlertTriangle className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
          ground truth: {c.is_fraud ? "fraud" : "legitimate"}
        </Badge>
      </div>

      <div className="mt-6">
        <SectionLabel>Reason codes (SHAP contribution)</SectionLabel>
        <div className="mt-3 space-y-2">
          {c.reason_codes.map((r, i) => {
            const w = (Math.abs(r.contribution) / maxAbs) * 100;
            const pos = r.contribution >= 0;
            return (
              <div key={r.feature} className="flex items-center gap-3 text-xs">
                <span className="w-36 shrink-0 truncate font-mono text-ink-faint">{r.feature}</span>
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-subtle">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${w}%` }}
                    transition={{ duration: 0.6, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                    className={`h-full rounded-full ${pos ? "bg-red" : "bg-blue"}`}
                  />
                </div>
                <span className={`w-14 text-right font-mono font-semibold ${pos ? "text-red" : "text-blue"}`}>
                  {r.contribution.toFixed(2)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {cf && (
        <div className="mt-6 rounded border border-accent-200 bg-accent-50/50 p-4">
          <div className="mb-1 flex items-center gap-1.5 text-accent-700">
            <GitCompareArrows className="h-4 w-4" />
            <SectionLabel>counterfactual</SectionLabel>
          </div>
          <p className="text-sm leading-relaxed text-ink-soft">
            If <span className="font-semibold text-ink">{cf.feature}</span> were {cf.to_value}{" "}
            instead of {cf.from_value}, risk would move{" "}
            <span className="font-mono text-red">{cf.risk_before.toFixed(2)}</span> {ARROW}{" "}
            <span className="font-mono text-blue">{cf.risk_after.toFixed(2)}</span>
            {drop > 0 && (
              <span className="font-semibold text-accent-700"> ({(drop * 100).toFixed(0)} pts lower)</span>
            )}
            .
          </p>
        </div>
      )}
    </Card>
  );
}
