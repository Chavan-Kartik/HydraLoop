"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldX, RefreshCw, Link2, Lock, FlaskConical } from "lucide-react";
import { getGovernance, Governance as GovData, latestRunId } from "@/lib/api";
import { tamperedCanonical, verifyChain } from "@/lib/chain";
import { Badge, Empty, ErrorBox, Card, Loading, OfflineBadge, Panel, SectionLabel } from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

const GENESIS = "0".repeat(32);

export function Governance() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [data, setData] = useState<GovData | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [tamperIndex, setTamperIndex] = useState<number | null>(null);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { runId } = await latestRunId();
      const { data, offline } = await getGovernance(runId ?? "seed");
      setData(data);
      setOffline(offline);
      setStatus(data.entries.length ? "ready" : "empty");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // The chain is recomputed here, in the browser, from the payload bytes the API
  // sent. The server's own verdict is deliberately not consulted.
  const tamper = useMemo(() => {
    if (tamperIndex === null || !data) return undefined;
    const target = data.entries[tamperIndex];
    const edited = tamperedCanonical(target?.canonical ?? "");
    return edited === null ? undefined : { index: tamperIndex, canonical: edited };
  }, [tamperIndex, data]);

  const result = useMemo(() => {
    if (!data) return null;
    return verifyChain(data.entries, data.genesis ?? GENESIS, tamper);
  }, [data, tamper]);

  const canRecompute = Boolean(data?.entries.some((e) => e.canonical));

  const reverify = useCallback(async () => {
    setVerifying(true);
    await load();
    setCheckedAt(new Date().toLocaleTimeString());
    setVerifying(false);
  }, [load]);

  if (status === "loading") return <Loading label="ledger" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (status === "empty" || !data || !result) return <Empty label="ledger entries" />;

  const ok = canRecompute ? result.verified : data.verified;
  const breakAt = canRecompute ? result.breakAt : data.break_at;

  return (
    <div className="space-y-4">
      {offline && <OfflineBadge />}

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <motion.span
              key={String(ok)}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 18 }}
              className={`grid h-14 w-14 place-items-center rounded-md ${
                ok ? "bg-success-50 text-success-700" : "bg-red/10 text-red"
              }`}
            >
              {ok ? <ShieldCheck className="h-7 w-7" /> : <ShieldX className="h-7 w-7" />}
            </motion.span>
            <div>
              <div className={`text-xl font-bold ${ok ? "text-success-700" : "text-red"}`}>
                {ok ? "Chain verified" : `Tamper detected at entry ${breakAt}`}
              </div>
              <div className="mt-0.5 flex items-center gap-2 font-mono text-xs text-ink-faint">
                <Lock className="h-3.5 w-3.5" />
                {data.length} entries, {data.algorithm ?? "blake2b-128"}, head{" "}
                {data.head_hash.slice(0, 14)}
              </div>
              <div className="mt-1 text-xs text-ink-ghost">
                {canRecompute
                  ? `Recomputed in this browser${checkedAt ? ` at ${checkedAt}` : ""}, not read from the API's verdict.`
                  : "This ledger was served without payload bytes, so the API's verdict is shown."}
              </div>
            </div>
          </div>
          <button
            onClick={reverify}
            disabled={verifying}
            className="inline-flex items-center gap-2 rounded border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink-soft transition-colors hover:border-accent-200 hover:text-ink disabled:opacity-40"
          >
            <RefreshCw className={`h-4 w-4 ${verifying ? "animate-spin" : ""}`} />
            {verifying ? "Verifying" : "Re-fetch and verify"}
          </button>
        </div>
      </Card>

      {canRecompute && (
        <Card className="p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <SectionLabel>prove it</SectionLabel>
              <p className="mt-1 max-w-2xl text-xs leading-relaxed text-ink-faint">
                Editing history should be detectable, so try it. This alters one number in the
                first entry&apos;s payload and re-runs the same check. The digest stops matching
                at that entry, and because every later entry commits to the one before it, the
                rest of the chain falls with it. Nothing is written to disk.
              </p>
            </div>
            <button
              onClick={() => setTamperIndex(tamperIndex === null ? 0 : null)}
              className={`inline-flex shrink-0 items-center gap-2 rounded border px-3 py-2 text-xs font-medium transition-colors ${
                tamperIndex === null
                  ? "border-line bg-surface text-ink-soft hover:border-accent-200 hover:text-ink"
                  : "border-red/40 bg-red/5 text-red"
              }`}
            >
              <FlaskConical className="h-3.5 w-3.5" />
              {tamperIndex === null ? "Tamper with entry 1" : "Restore the real payload"}
            </button>
          </div>
        </Card>
      )}

      <Panel title="Hash-chained generation ledger" right={<Link2 className="h-4 w-4 text-accent-700" />}>
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-widest text-ink-ghost">
                <th className="pb-2 pr-3 font-semibold">Gen</th>
                <th className="pb-2 pr-3 font-semibold">Decision</th>
                <th className="pb-2 pr-3 font-semibold">Escape rate</th>
                <th className="pb-2 pr-3 font-semibold">prev_hash</th>
                <th className="pb-2 pr-3 font-semibold">stored</th>
                <th className="pb-2 pr-3 font-semibold">recomputed</th>
                <th className="pb-2 pr-3 font-semibold">Link</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {result.entries.map((e, i) => {
                const rowOk = canRecompute ? e.digestOk && e.linkOk : e.link_ok;
                return (
                  <motion.tr
                    key={`${e.entry_hash}-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className={`border-t border-line ${rowOk ? "" : "bg-red/5"}`}
                  >
                    <td className="py-2 pr-3 text-ink-faint">{e.generation}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={e.promoted ? "blue" : "slate"}>
                        {e.promoted ? "promote" : "hold"}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-red">{(e.escape_rate * 100).toFixed(1)}%</td>
                    <td className="py-2 pr-3 text-ink-ghost">{e.prev_hash.slice(0, 10)}</td>
                    <td className="py-2 pr-3 text-ink-soft">{e.entry_hash.slice(0, 10)}</td>
                    <td
                      className={`py-2 pr-3 ${e.digestOk ? "text-ink-soft" : "font-bold text-red"}`}
                    >
                      {canRecompute ? e.recomputed.slice(0, 10) : "-"}
                    </td>
                    <td className="py-2 pr-3">
                      <span
                        className={`inline-flex items-center gap-1 font-semibold ${rowOk ? "text-success-700" : "text-red"}`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${rowOk ? "bg-success-500" : "bg-red"}`}
                        />
                        {rowOk ? "ok" : !e.digestOk ? "digest" : "link"}
                      </span>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-ink-faint">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-700" />
          <span>
            <span className="font-semibold text-ink-soft">stored</span> is the digest written when
            the generation was sealed.{" "}
            <span className="font-semibold text-ink-soft">recomputed</span> is what this page just
            derived from the payload with {data.algorithm ?? "blake2b-128"}. They match only if
            the payload is byte-identical to the one that was sealed, and since each entry commits
            to the previous digest, a single edit anywhere breaks every entry after it.
          </span>
        </p>
      </Panel>
    </div>
  );
}
