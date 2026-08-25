"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldX, RefreshCw, Link2, Lock } from "lucide-react";
import { getGovernance, Governance as GovData, latestRunId } from "@/lib/api";
import { Badge, Empty, ErrorBox, Card, Loading, OfflineBadge, Panel } from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

export function Governance() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [data, setData] = useState<GovData | null>(null);
  const [verifying, setVerifying] = useState(false);

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

  const reverify = useCallback(async () => {
    setVerifying(true);
    await load();
    setTimeout(() => setVerifying(false), 500);
  }, [load]);

  if (status === "loading") return <Loading label="ledger" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (status === "empty" || !data) return <Empty label="ledger entries" />;

  const ok = data.verified;

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
                {ok ? "Chain verified" : `Tamper detected at entry ${data.break_at}`}
              </div>
              <div className="mt-0.5 flex items-center gap-2 font-mono text-xs text-ink-faint">
                <Lock className="h-3.5 w-3.5" />
                {data.length} entries, head {data.head_hash.slice(0, 14)}
              </div>
            </div>
          </div>
          <button
            onClick={reverify}
            disabled={verifying}
            className="inline-flex items-center gap-2 rounded border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink-soft transition-colors hover:border-accent-200 hover:text-ink disabled:opacity-40"
          >
            <RefreshCw className={`h-4 w-4 ${verifying ? "animate-spin" : ""}`} />
            {verifying ? "Verifying" : "Verify chain"}
          </button>
        </div>
      </Card>

      <Panel title="Hash-chained generation ledger" right={<Link2 className="h-4 w-4 text-accent-700" />}>
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-widest text-ink-ghost">
                <th className="pb-2 pr-3 font-semibold">Gen</th>
                <th className="pb-2 pr-3 font-semibold">Decision</th>
                <th className="pb-2 pr-3 font-semibold">Escape rate</th>
                <th className="pb-2 pr-3 font-semibold">prev_hash</th>
                <th className="pb-2 pr-3 font-semibold">entry_hash</th>
                <th className="pb-2 pr-3 font-semibold">Link</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {data.entries.map((e, i) => (
                <motion.tr
                  key={e.entry_hash}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
                  className="border-t border-line"
                >
                  <td className="py-2 pr-3 text-ink-faint">{e.generation}</td>
                  <td className="py-2 pr-3">
                    <Badge tone={e.promoted ? "blue" : "slate"}>{e.promoted ? "promote" : "hold"}</Badge>
                  </td>
                  <td className="py-2 pr-3 text-red">{(e.escape_rate * 100).toFixed(1)}%</td>
                  <td className="py-2 pr-3 text-ink-ghost">{e.prev_hash.slice(0, 10)}</td>
                  <td className="py-2 pr-3 text-ink-soft">{e.entry_hash.slice(0, 10)}</td>
                  <td className="py-2 pr-3">
                    <span className={`inline-flex items-center gap-1 font-semibold ${e.link_ok ? "text-success-700" : "text-red"}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${e.link_ok ? "bg-success-500" : "bg-red"}`} />
                      {e.link_ok ? "ok" : "broken"}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-ink-faint">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-700" />
          Each entry embeds the previous entry&apos;s digest, so any edit to run history breaks the
          chain on the next verification, the tamper-evidence behind the responsible-AI story.
        </p>
      </Panel>
    </div>
  );
}
