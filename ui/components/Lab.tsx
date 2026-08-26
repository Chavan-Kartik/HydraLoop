"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Play } from "lucide-react";
import {
  LabCase,
  LabEvent,
  LabHighlight,
  LabResult,
  LabStep,
  streamLab,
} from "@/lib/api";
import {
  ARROW,
  Badge,
  ErrorBox,
  GhostButton,
  Card,
  PrimaryButton,
  Panel,
  SectionLabel,
} from "./ui";
import { Harden } from "./Harden";

const CACHE_KEY = "hydraloop-lab-last";

const PRESETS: { id: string; label: string; text: string }[] = [
  {
    id: "agentic",
    label: "Agentic mandate drift",
    text: "An autonomous shopping agent holds a delegated spending mandate and starts placing purchases at machine cadence, drifting past the intended value band with almost no human dwell.",
  },
  {
    id: "testing",
    label: "Card-testing swarm",
    text: "Card testing: a swarm of rotating devices places many low-value card-not-present authorisations in a short window to learn which amounts clear.",
  },
  {
    id: "app",
    label: "Authorised push-payment",
    text: "A victim is talked into sending authorised push payments to novel payees, then funds fan out through a short mule chain.",
  },
];

/**
 * What to tell someone whose "Run" click could not reach the backend.
 *
 * The advice differs by who they are. On localhost it is a developer who has not
 * started the API yet, so give them the command. On a deployed origin it is a
 * visitor who cannot start anything, so say what they are looking at instead of
 * asking them to open a terminal.
 */
function unreachableBackendHint(): string {
  const local =
    typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (local) {
    return (
      "The Lab could not reach the API. Usually this is either (1) the API is not running, or " +
      "(2) the browser blocked the request because the UI is on a different localhost port. " +
      "Check the UI URL port in the address bar, then open http://127.0.0.1:8000/api/health in a new tab. " +
      "If health fails, start the API in a second terminal: activate .venv, then run python -m hydraloop api."
    );
  }
  return (
    "This deployment has no live backend attached, so the pipeline cannot run here. " +
    "The read-only screens are showing a recorded snapshot. To run it live, clone the " +
    "repository and follow the quickstart in the README."
  );
}

const PIPELINE: { id: string; title: string; hint: string }[] = [
  { id: "identify", title: "Identify", hint: "Map text to a family and signals" },
  { id: "generate", title: "Generate", hint: "Clamp a schema-valid genome" },
  { id: "simulate", title: "Simulate", hint: "Run it in the payment twin" },
  { id: "detect", title: "Detect", hint: "Train, score, decide" },
  { id: "investigate", title: "Investigate", hint: "SHAP + counterfactual" },
];

type Phase = "idle" | "running" | "done" | "fail";

function nowStamp() {
  return new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function Lab() {
  const params = useSearchParams();
  const [text, setText] = useState(PRESETS[0].text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [log, setLog] = useState<{ t: string; msg: string }[]>([]);
  const [phases, setPhases] = useState<Record<string, Phase>>(
    Object.fromEntries(PIPELINE.map((p) => [p.id, "idle"])),
  );
  const [steps, setSteps] = useState<Record<string, LabStep>>({});
  const [result, setResult] = useState<Partial<LabResult>>({});
  const [selected, setSelected] = useState<LabCase | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bootstrapped = useRef(false);

  const applyEvent = (ev: LabEvent) => {
    if (ev.type === "status") {
      setPhases((p) => ({ ...p, [ev.phase]: "running" }));
      setLog((rows) => [...rows.slice(-24), { t: nowStamp(), msg: ev.message }]);
    }
    if (ev.type === "step") {
      setSteps((s) => ({ ...s, [ev.step.id]: ev.step }));
      setPhases((p) => ({ ...p, [ev.step.id]: ev.step.ok ? "done" : "fail" }));
    }
    if (ev.type === "identity") {
      setResult((r) => ({
        ...r,
        family: ev.family,
        attack_name: ev.attack_name,
        method: ev.method,
        signals: ev.signals,
        genome_id: ev.genome_id,
      }));
    }
    if (ev.type === "genome") {
      setResult((r) => ({ ...r, brief: ev.brief, highlights: ev.highlights }));
    }
    if (ev.type === "sim") {
      setResult((r) => ({
        ...r,
        stats: {
          n_txns: ev.n_txns,
          n_fraud: ev.n_fraud,
          n_legit: ev.n_legit,
          caught: r.stats?.caught,
          escaped: r.stats?.escaped,
          false_positives: r.stats?.false_positives,
        },
      }));
    }
    if (ev.type === "scores") {
      setResult((r) => ({ ...r, stats: ev.stats, txns: ev.txns }));
    }
    if (ev.type === "cases") {
      setResult((r) => ({ ...r, cases: ev.cases }));
      setSelected(ev.cases[0] ?? null);
    }
    if (ev.type === "done") {
      setResult(ev.result);
      setSelected(ev.result.cases[0] ?? null);
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(ev.result));
      } catch {
        /* ignore quota */
      }
    }
  };

  const run = async (input?: string) => {
    const payload = (input ?? text).trim();
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setBusy(true);
    setError("");
    setLog([{ t: nowStamp(), msg: `Starting Identify ${ARROW} Detect on this description.` }]);
    setPhases(Object.fromEntries(PIPELINE.map((p) => [p.id, "idle"])));
    setSteps({});
    setResult({});
    setSelected(null);
    try {
      await streamLab(payload, applyEvent, ctrl.signal);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setError(
        (e as Error).message.includes("Failed to fetch")
          ? unreachableBackendHint()
          : (e as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    const fromUrl = params.get("text");
    const force = params.get("run") === "1";
    if (fromUrl) setText(fromUrl);
    if (force || fromUrl) {
      void run(fromUrl || PRESETS[0].text);
      return;
    }
    try {
      const cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        const data = JSON.parse(cached) as LabResult;
        setResult(data);
        setSelected(data.cases?.[0] ?? null);
        setSteps(Object.fromEntries((data.steps ?? []).map((s) => [s.id, s])));
        setPhases(Object.fromEntries(PIPELINE.map((p) => [p.id, data.steps?.some((s) => s.id === p.id) ? "done" : "idle"])));
        setLog([{ t: nowStamp(), msg: "Restored the last lab run. Edit the text and press Run to try another pattern." }]);
        return;
      }
    } catch {
      /* ignore */
    }
    void run(PRESETS[0].text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const highlights = result.highlights ?? [];
  const txns = result.txns ?? [];
  const cases = result.cases ?? [];
  const stats = result.stats;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-accent-700">
          Live lab
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink">
          Type a fraud pattern. Watch every step.
        </h1>
        <p className="mt-2 max-w-3xl text-[14px] leading-relaxed text-ink-faint">
          Describe cadence, devices, amounts, not a how-to. The mapper picks a family, the DSL
          clamps a genome, the payment twin emits transactions, a detector scores them, and the
          investigation pane opens with SHAP reason codes. A demo run starts on first load.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <GhostButton
              key={p.id}
              active={text === p.text}
              onClick={() => {
                setText(p.text);
                void run(p.text);
              }}
            >
              {p.label}
            </GhostButton>
          ))}
        </div>
        <label className="mt-4 block">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-ghost">
            Threat description
          </span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, 600))}
            rows={4}
            className="mt-1.5 w-full rounded border-2 border-navy/30 bg-white p-3 text-[14px] text-ink outline-none focus:border-navy"
            placeholder="Describe the behavioural pattern (cadence, devices, amounts)"
          />
        </label>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <PrimaryButton onClick={() => void run()} disabled={busy || text.trim().length < 12}>
            <Play className="h-3.5 w-3.5" />
            {busy ? "Running pipeline..." : `Run Identify ${ARROW} Detect`}
          </PrimaryButton>
          <span className="text-[12px] text-ink-ghost">{text.length}/600</span>
        </div>
      </Card>

      {error && <ErrorBox message={error} />}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="space-y-3">
          <Panel title="Pipeline">
            <ol className="space-y-0">
              {PIPELINE.map((p, i) => {
                const state = phases[p.id];
                const step = steps[p.id];
                return (
                  <li key={p.id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span
                        className={`mt-0.5 grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold ${
                          state === "running"
                            ? "animate-pulse bg-accent-600 text-white"
                            : state === "done"
                              ? "bg-success-500 text-white"
                              : state === "fail"
                                ? "bg-red text-white"
                                : "bg-subtle text-ink-ghost"
                        }`}
                      >
                        {i + 1}
                      </span>
                      {i < PIPELINE.length - 1 && <span className="my-1 w-px flex-1 bg-line" />}
                    </div>
                    <div className="min-w-0 pb-4">
                      <div className="text-[13px] font-semibold text-ink">{p.title}</div>
                      <div className="text-[12px] text-ink-ghost">{step?.detail ?? p.hint}</div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Panel>

          <Panel title="Live log">
            <div className="scroll-thin max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-ink-soft">
              {log.length === 0 ? (
                <div className="text-ink-ghost">Waiting to start</div>
              ) : (
                log.map((row, i) => (
                  <div key={`${row.t}-${i}`}>
                    <span className="text-ink-ghost">{row.t}</span> {row.msg}
                  </div>
                ))
              )}
            </div>
          </Panel>
        </div>

        <div className="space-y-3">
          {(result.family || highlights.length > 0) && (
            <Panel
              title="Constrained genome"
              right={result.family ? <Badge tone="brand">{result.family}</Badge> : undefined}
            >
              {result.brief && <p className="text-[13px] leading-relaxed text-ink-soft">{result.brief}</p>}
              {result.signals && result.signals.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {result.signals.map((s) => (
                    <span key={s} className="rounded-md bg-subtle px-2 py-0.5 font-mono text-[10px] text-ink-soft">
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {highlights.length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {highlights.map((h: LabHighlight) => (
                    <div key={h.label} className="border border-line bg-subtle/60 px-2 py-1.5">
                      <div className="text-[10px] uppercase tracking-wide text-ink-ghost">{h.label}</div>
                      <div className="font-mono text-[12px] font-semibold text-ink">{h.value}</div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          )}

          {stats && (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Transactions" value={String(stats.n_txns ?? "-")} />
              <Stat label="Attack txns" value={String(stats.n_fraud ?? "-")} />
              <Stat label="Caught" value={String(stats.caught ?? "-")} />
              <Stat label="Escaped" value={String(stats.escaped ?? "-")} />
            </div>
          )}

          <Panel title="Scored traffic (click a row)">
            {txns.length === 0 ? (
              <div className="text-[13px] text-ink-ghost">
                {busy ? "Twin is still emitting transactions" : "No scored rows yet."}
              </div>
            ) : (
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-ink-ghost">
                    <th className="py-1">Txn</th>
                    <th>Truth</th>
                    <th>Amount</th>
                    <th>Risk</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {txns.map((t) => (
                    <tr
                      key={t.txn_id}
                      onClick={() => {
                        const c = cases.find((x) => x.txn_id === t.txn_id);
                        if (c) setSelected(c);
                      }}
                      className={`cursor-pointer border-t border-line ${
                        selected?.txn_id === t.txn_id ? "bg-subtle" : ""
                      }`}
                    >
                      <td className="py-1.5 font-mono text-[11px]">{t.txn_id.slice(0, 18)}</td>
                      <td>{t.is_fraud ? "fraud" : "legit"}</td>
                      <td className="font-mono">{(t.amount_minor / 100).toFixed(2)}</td>
                      <td className="font-mono">{t.risk_score.toFixed(2)}</td>
                      <td>{t.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          <Panel title="Investigation">
            {selected ? (
              <CaseView c={selected} />
            ) : (
              <div className="text-[13px] text-ink-ghost">
                {busy ? "Waiting for SHAP explanations..." : "Select a scored transaction."}
              </div>
            )}
          </Panel>
        </div>
      </div>

      <Harden text={text} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line bg-surface px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-ghost">{label}</div>
      <div className="font-mono text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function CaseView({ c }: { c: LabCase }) {
  const maxAbs = Math.max(...c.reason_codes.map((r) => Math.abs(r.contribution)), 1);
  const cf = c.counterfactual;
  return (
    <div className="space-y-3 text-[13px]">
      <div className="flex items-center justify-between">
        <div>
          <SectionLabel>risk</SectionLabel>
          <div className="font-mono text-2xl font-semibold">{c.risk_score.toFixed(3)}</div>
        </div>
        <Badge tone={c.is_fraud ? "red" : "green"}>{c.is_fraud ? "fraud" : "legit"}</Badge>
      </div>
      <div>
        <SectionLabel>SHAP reason codes</SectionLabel>
        {c.reason_codes.length === 0 && (
          <p className="mt-2 text-[12px] text-ink-ghost">
            The explainer could not run on this row, so there is nothing to show here.
          </p>
        )}
        <div className="mt-2 space-y-1">
          {c.reason_codes.map((r) => (
            <div key={r.feature} className="flex items-center gap-2 text-[12px]">
              <span className="w-28 truncate font-mono text-ink-faint">{r.feature}</span>
              <div className="h-2 flex-1 bg-subtle">
                <div
                  className={`h-2 ${r.contribution >= 0 ? "bg-red" : "bg-navy"}`}
                  style={{ width: `${(Math.abs(r.contribution) / maxAbs) * 100}%` }}
                />
              </div>
              <span className="w-12 text-right font-mono">{r.contribution.toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>
      {cf && (
        <p className="border border-line bg-subtle p-2 text-[12px] text-ink-soft">
          If <span className="font-semibold text-ink">{cf.feature}</span> were {cf.to_value} instead of{" "}
          {cf.from_value}, risk {cf.risk_before.toFixed(2)} {ARROW} {cf.risk_after.toFixed(2)}.
        </p>
      )}
    </div>
  );
}
