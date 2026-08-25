"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  Fingerprint,
  Repeat,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  XCircle,
} from "lucide-react";
import {
  HardenEvent,
  HardenGauntlet,
  HardenResult,
  HardenSide,
  HardenTxn,
  streamHarden,
} from "@/lib/api";
import {
  ARROW,
  Badge,
  ErrorBox,
  Card,
  PrimaryButton,
  Panel,
  SectionLabel,
} from "./ui";

const STAGES = [
  { id: "incumbent", title: "Incumbent on duty", hint: "Trained on other families only" },
  { id: "escape", title: "The attack escapes", hint: "Wave 1 against the live model" },
  { id: "harden", title: "Harden", hint: "Immune memory, then retrain" },
  { id: "gauntlet", title: "Regression gauntlet", hint: "Must not forget the old attacks" },
  { id: "verdict", title: "Re-attack", hint: "Wave 2, rows never seen" },
];

type State = "idle" | "active" | "done";

function money(minor: number) {
  return (minor / 100).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

export function Harden({ text }: { text: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState<Record<string, State>>({});
  const [log, setLog] = useState<string[]>([]);
  const [incumbent, setIncumbent] = useState<Extract<HardenEvent, { type: "incumbent" }> | null>(null);
  const [escape, setEscape] = useState<Extract<HardenEvent, { type: "escape" }> | null>(null);
  const [gauntlet, setGauntlet] = useState<HardenGauntlet | null>(null);
  const [verdict, setVerdict] = useState<Extract<HardenEvent, { type: "verdict" }> | null>(null);
  const [ledger, setLedger] = useState<Extract<HardenEvent, { type: "ledger" }> | null>(null);
  const [result, setResult] = useState<HardenResult | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const apply = (ev: HardenEvent) => {
    switch (ev.type) {
      case "status":
        setStage((s) => ({ ...s, [ev.phase]: "active" }));
        setLog((rows) => [...rows.slice(-14), ev.message]);
        break;
      case "incumbent":
        setIncumbent(ev);
        setStage((s) => ({ ...s, incumbent: "done" }));
        break;
      case "escape":
        setEscape(ev);
        setStage((s) => ({ ...s, escape: "done" }));
        break;
      case "candidate":
        setStage((s) => ({ ...s, harden: "done" }));
        setLog((rows) => [...rows.slice(-14), ev.detail]);
        break;
      case "gauntlet":
        setGauntlet(ev);
        setStage((s) => ({ ...s, gauntlet: "done" }));
        break;
      case "verdict":
        setVerdict(ev);
        setStage((s) => ({ ...s, verdict: "done" }));
        break;
      case "ledger":
        setLedger(ev);
        break;
      case "done":
        setResult(ev.result);
        break;
    }
  };

  const run = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setBusy(true);
    setError("");
    setStage({});
    setLog([]);
    setIncumbent(null);
    setEscape(null);
    setGauntlet(null);
    setVerdict(null);
    setLedger(null);
    setResult(null);
    try {
      await streamHarden(text, apply, ctrl.signal);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setError(
        (e as Error).message.includes("Failed to fetch")
          ? "API is not running. In the other terminal: python -m hydraloop api"
          : (e as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-accent-700">
            <Repeat className="h-3.5 w-3.5" />
            Close the loop
          </div>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-ink">
            Let this attack escape, then make the defense learn it
          </h2>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-faint">
            The live detector is trained on <em>other</em> attack families, so what you described is a
            genuine zero-day to it. Whatever slips through enters immune memory, a candidate retrains,
            and it must clear the regression gauntlet before it can go live. The result is then
            measured on a <strong>second wave of the same attack against a fresh population</strong>,
            so the improvement cannot come from memorising the rows it trained on. Both models are
            judged at the same 1% false-positive budget.
          </p>
        </div>
        <PrimaryButton onClick={run} disabled={busy || text.trim().length < 12}>
          <ShieldCheck className="h-3.5 w-3.5" />
          {busy ? "Running the loop..." : "Let it escape, then harden"}
        </PrimaryButton>
      </div>

      {error && (
        <div className="mt-4">
          <ErrorBox message={error} />
        </div>
      )}

      {(busy || incumbent) && (
        <div className="mt-5 grid gap-2 sm:grid-cols-5">
          {STAGES.map((s, i) => {
            const st = stage[s.id] ?? "idle";
            return (
              <div
                key={s.id}
                className={`border p-2.5 ${
                  st === "done"
                    ? "border-line bg-surface"
                    : st === "active"
                      ? "animate-pulse border-accent-200 bg-accent-50"
                      : "border-dashed border-line bg-subtle/40"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className={`grid h-4 w-4 place-items-center rounded-full text-[9px] font-bold ${
                      st === "done"
                        ? "bg-success-500 text-white"
                        : st === "active"
                          ? "bg-accent-600 text-white"
                          : "bg-subtle text-ink-ghost"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className="text-[11px] font-semibold text-ink">{s.title}</span>
                </div>
                <div className="mt-0.5 text-[10px] leading-snug text-ink-ghost">{s.hint}</div>
              </div>
            );
          })}
        </div>
      )}

      {log.length > 0 && (
        <div className="mt-3 border border-line bg-subtle/50 p-2.5 font-mono text-[11px] leading-relaxed text-ink-soft">
          {log.map((row, i) => (
            <div key={i}>{row}</div>
          ))}
        </div>
      )}

      {escape && (
        <div className="mt-4 border-l-2 border-red bg-[#fdecee] p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-red">
            <ShieldAlert className="h-3.5 w-3.5" />
            Escape detected
          </div>
          <p className="mt-1 text-[13px] text-ink-soft">
            <strong className="font-mono">{escape.escaped}</strong> of {escape.n_fraud} attack
            transactions slipped past the incumbent, worth{" "}
            <strong className="font-mono">{money(escape.escaped_value_minor)}</strong> in settled
            value. Incumbent recall on this pattern: {pct(escape.recall)}.
          </p>
        </div>
      )}

      {gauntlet && <GauntletBanner g={gauntlet} />}

      {verdict && (
        <BeforeAfter
          before={verdict.before}
          after={verdict.after}
          nFraud={verdict.n_fraud}
          nLegit={verdict.n_legit}
          newlyCaught={verdict.newly_caught}
          valueRecovered={verdict.value_recovered_minor}
          promoted={gauntlet?.promote ?? false}
        />
      )}

      {verdict && verdict.txns.length > 0 && (
        <div className="mt-4">
          <Panel title="Transactions the retrain moved most (wave 2, unseen)">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-ink-ghost">
                  <th className="py-1">Txn</th>
                  <th>Value</th>
                  <th>Risk before</th>
                  <th>Risk after</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {verdict.txns.map((t) => (
                  <TxnRow key={t.txn_id} t={t} />
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
      )}

      {ledger && result && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border border-line bg-subtle/50 p-2.5 text-[11px] text-ink-soft">
          <Fingerprint className="h-3.5 w-3.5 text-accent-700" />
          <span>
            Written to the hash-chained ledger as generation {ledger.generation} of{" "}
            {ledger.chain_length}.
          </span>
          <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-[10px]">
            {ledger.entry_hash.slice(0, 24)}
          </code>
          <span className="text-ink-ghost">
            Genome {result.genome_id} &middot; family {result.family}
          </span>
        </div>
      )}
    </Card>
  );
}

function GauntletBanner({ g }: { g: HardenGauntlet }) {
  const ok = g.promote;
  return (
    <div
      className={`mt-4 border-l-2 p-3 ${ok ? "border-emerald-500 bg-success-50" : "border-amber-500 bg-warn-50"}`}
    >
      <div
        className={`flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider ${
          ok ? "text-success-700" : "text-warn-700"
        }`}
      >
        {ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
        {ok ? "Gauntlet passed: candidate promoted" : "Gauntlet blocked: incumbent stays live"}
      </div>
      <p className="mt-1 font-mono text-[12px] text-ink-soft">{g.reason}</p>
      <p className="mt-1.5 text-[12px] text-ink-faint">
        {ok ? (
          <>
            Recall on the archive of previously-known attacks held at{" "}
            {pct(g.candidate_recall)} (was {pct(g.incumbent_recall)}), false-positive rate{" "}
            {pct(g.candidate_fpr)}, calibration error {g.candidate_ece.toFixed(3)}. The swap is an
            atomic file replace, so a rollback needs no undo.
          </>
        ) : (
          <>
            The candidate learned the new attack, but its recall on previously-known families moved{" "}
            {pct(g.incumbent_recall)} {ARROW} {pct(g.candidate_recall)}. That is catastrophic
            forgetting, so the gate refused the promotion and production kept the older model. The
            comparison below shows what the rejected candidate <em>would</em> have done.
          </>
        )}
      </p>
    </div>
  );
}

function BeforeAfter({
  before,
  after,
  nFraud,
  nLegit,
  newlyCaught,
  valueRecovered,
  promoted,
}: {
  before: HardenSide;
  after: HardenSide;
  nFraud: number;
  nLegit: number;
  newlyCaught: number;
  valueRecovered: number;
  promoted: boolean;
}) {
  return (
    <div className="mt-4">
      <SectionLabel>
        Wave 2 {ARROW} the same attack, a fresh population, {nFraud} attack and {nLegit} legitimate
        transactions neither model has seen
      </SectionLabel>
      <div className="mt-2 grid gap-3 md:grid-cols-[1fr_auto_1fr]">
        <SideCard label="Incumbent" side={before} tone="red" />
        <div className="flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <div className="font-mono text-2xl font-bold text-accent-700">{ARROW}</div>
            <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-ink-ghost">
              retrain
            </div>
          </motion.div>
        </div>
        <SideCard
          label={promoted ? "Hardened (live)" : "Candidate (rejected)"}
          side={after}
          tone="green"
        />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Headline
          label="Attacks newly caught"
          value={`+${newlyCaught}`}
          detail={`of ${nFraud} in this wave`}
        />
        <Headline
          label="Value no longer escaping"
          value={money(valueRecovered)}
          detail="settled attack value"
        />
        <Headline
          label="False-positive cost"
          value={`${pct(before.fpr)} ${ARROW} ${pct(after.fpr)}`}
          detail="1% budget, measured on fresh legit traffic"
        />
      </div>
    </div>
  );
}

function SideCard({ label, side, tone }: { label: string; side: HardenSide; tone: "red" | "green" }) {
  const accent = tone === "red" ? "text-red" : "text-success-700";
  return (
    <div className="border border-line bg-surface p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-ghost">{label}</div>
      <div className={`mt-1 font-mono text-xl font-bold tabular-nums ${accent}`}>
        {pct(side.recall)}
      </div>
      <div className="text-[11px] text-ink-ghost">recall on this attack</div>
      <dl className="mt-2 space-y-0.5 text-[11px] text-ink-soft">
        <Row k="Caught" v={String(side.caught)} />
        <Row k="Escaped" v={String(side.escaped)} />
        <Row k="Value escaped" v={money(side.escaped_value_minor)} />
        <Row k="False positives" v={`${side.false_positives} (${pct(side.fpr)})`} />
      </dl>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-ink-ghost">{k}</dt>
      <dd className="font-mono">{v}</dd>
    </div>
  );
}

function Headline({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border border-line bg-subtle/50 px-3 py-2">
      <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-ink-ghost">
        <TrendingDown className="h-3 w-3" />
        {label}
      </div>
      <div className="font-mono text-base font-bold tabular-nums text-ink">{value}</div>
      <div className="text-[10px] text-ink-ghost">{detail}</div>
    </div>
  );
}

function TxnRow({ t }: { t: HardenTxn }) {
  const flipped = !t.caught_before && t.caught_after;
  return (
    <tr className="border-t border-line">
      <td className="py-1.5 font-mono text-[11px]">{t.txn_id.slice(0, 18)}</td>
      <td className="font-mono">{money(t.amount_minor)}</td>
      <td className="font-mono text-ink-ghost">{t.before.toFixed(3)}</td>
      <td className="font-mono font-semibold text-ink">{t.after.toFixed(3)}</td>
      <td>
        {flipped ? (
          <Badge tone="green">now caught</Badge>
        ) : t.caught_after ? (
          <Badge tone="slate">already caught</Badge>
        ) : (
          <Badge tone="red">still escaping</Badge>
        )}
      </td>
    </tr>
  );
}
