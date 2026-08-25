"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { GitBranch, Bot, ArrowRight, FlaskConical } from "lucide-react";
import { getLineage, latestRunId, Lineage as LineageData, LineageNode } from "@/lib/api";
import { Badge, Empty, ErrorBox, Loading, OfflineBadge, Panel, SectionLabel } from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

export function Lineage() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [data, setData] = useState<LineageData | null>(null);
  const [selected, setSelected] = useState<LineageNode | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { runId } = await latestRunId();
        const { data, offline } = await getLineage(runId ?? "seed");
        setData(data);
        setOffline(offline);
        setSelected(data.nodes[0] ?? null);
        setStatus(data.nodes.length ? "ready" : "empty");
      } catch (e) {
        setError((e as Error).message);
        setStatus("error");
      }
    })();
  }, []);

  const byGeneration = useMemo(() => {
    const map = new Map<number, LineageNode[]>();
    (data?.nodes ?? []).forEach((n) => {
      const list = map.get(n.generation) ?? [];
      list.push(n);
      map.set(n.generation, list);
    });
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [data]);

  if (status === "loading") return <Loading label="lineage" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (status === "empty" || !data) return <Empty label="lineage" />;

  return (
    <div className="space-y-4">
      {offline && <OfflineBadge />}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Panel title="Escape-mode lineage by generation">
            <div className="scroll-thin flex items-stretch gap-3 overflow-x-auto pb-2">
              {byGeneration.map(([gen, nodes], gi) => (
                <div key={gen} className="flex items-stretch gap-3">
                  <div className="min-w-[160px]">
                    <div className="mb-2 flex items-center justify-center">
                      <span className="rounded-full border border-line bg-subtle px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-ink-faint">
                        Gen {gen}
                      </span>
                    </div>
                    <div className="space-y-2">
                      {nodes.map((n) => {
                        const active = selected?.id === n.id;
                        const agentic = n.family === "agentic_commerce";
                        return (
                          <motion.button
                            key={n.id}
                            layout
                            whileHover={{ scale: 1.02 }}
                            onClick={() => setSelected(n)}
                            className={`w-full rounded border p-2.5 text-left transition-colors ${
                              active
                                ? "border-accent-200 bg-accent-50 shadow-card"
                                : agentic
                                  ? "border-accent-200 bg-surface"
                                  : "border-line bg-surface hover:border-accent-200"
                            }`}
                          >
                            <div className="flex items-center gap-1.5">
                              {agentic && <Bot className="h-3.5 w-3.5 text-accent-700" />}
                              <span className="font-mono text-xs font-bold text-ink">
                                {n.attack_id}
                              </span>
                            </div>
                            <div className="mt-0.5 truncate font-mono text-[10px] text-ink-ghost">
                              {n.genome_id}
                            </div>
                            <div className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-red">
                              <span className="h-1.5 w-1.5 rounded-full bg-red" />{n.size} escaped
                            </div>
                          </motion.button>
                        );
                      })}
                    </div>
                  </div>
                  {gi < byGeneration.length - 1 && (
                    <div className="flex items-center text-ink-ghost">
                      <ArrowRight className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <Panel title="Attack brief" right={<GitBranch className="h-4 w-4 text-accent-700" />}>
          {selected ? (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-3"
            >
              <div className="flex items-center gap-2">
                <span className="grid h-10 w-10 place-items-center rounded bg-accent-600 text-white">
                  <FlaskConical className="h-5 w-5" />
                </span>
                <div>
                  <div className="font-mono text-sm font-bold text-ink">{selected.attack_id}</div>
                  <Badge tone={selected.family === "agentic_commerce" ? "brand" : "slate"}>
                    {selected.family.replace(/_/g, " ")}
                  </Badge>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-ink-soft">
                {selected.brief || "No brief recorded for this genome."}
              </p>
              <div className="rounded border border-line bg-subtle/50 p-3">
                <SectionLabel>trace</SectionLabel>
                <div className="mt-1 font-mono text-[11px] text-ink-faint">
                  genome {selected.genome_id}, generation {selected.generation}, {selected.size}{" "}
                  txns escaped
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="text-sm text-ink-ghost">Select a node to read its brief.</div>
          )}
        </Panel>
      </div>
    </div>
  );
}
