"use client";

import { useEffect, useState } from "react";
import { TrendingDown, ShieldCheck, Layers, RotateCcw, Target } from "lucide-react";
import { getKpis, Kpis, latestRunId } from "@/lib/api";
import { AnimatedNumber, ARROW } from "./ui";

type Cell = {
  label: string;
  icon: typeof Target;
  render: (k: Kpis | null) => React.ReactNode;
  accent: string;
};

const pctFmt = (n: number) => `${Math.round(n)}%`;

const CELLS: Cell[] = [
  {
    label: "Escape rate",
    icon: TrendingDown,
    accent: "text-red",
    render: (k) =>
      k?.escape_rate_end !== undefined ? (
        <span className="flex items-baseline gap-1.5">
          <span className="text-ink-ghost">
            <AnimatedNumber value={(k.escape_rate_start ?? 0) * 100} format={pctFmt} />
          </span>
          <span className="text-ink-ghost">{ARROW}</span>
          <span className="text-red">
            <AnimatedNumber value={(k.escape_rate_end ?? 0) * 100} format={pctFmt} />
          </span>
        </span>
      ) : (
        "-"
      ),
  },
  {
    label: "Attacker ROI",
    icon: TrendingDown,
    accent: "text-accent-700",
    render: (k) =>
      k?.attacker_roi_start !== undefined ? (
        <span className="flex items-baseline gap-1.5">
          <span className="text-ink-ghost">
            <AnimatedNumber value={k.attacker_roi_start ?? 0} format={(n) => `${n.toFixed(1)}x`} />
          </span>
          <span className="text-ink-ghost">{ARROW}</span>
          <span className="text-accent-700">
            <AnimatedNumber value={k.attacker_roi_end ?? 0} format={(n) => `${n.toFixed(1)}x`} />
          </span>
        </span>
      ) : (
        <span className="text-accent-700">collapses</span>
      ),
  },
  {
    label: "Best recall",
    icon: Target,
    accent: "text-accent-500",
    render: (k) =>
      k?.best_archive_recall !== undefined ? (
        <span className="text-accent-500">
          <AnimatedNumber value={(k.best_archive_recall ?? 0) * 100} format={pctFmt} />
        </span>
      ) : (
        "-"
      ),
  },
  {
    label: "Rollbacks blocked",
    icon: RotateCcw,
    accent: "text-ink",
    render: (k) => <AnimatedNumber value={k?.rollbacks ?? 0} />,
  },
  {
    label: "Generations",
    icon: Layers,
    accent: "text-ink",
    render: (k) => <AnimatedNumber value={k?.generations ?? 0} />,
  },
];

export function KpiBar() {
  const [kpis, setKpis] = useState<Kpis | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { runId } = await latestRunId();
        const { data } = await getKpis(runId ?? "seed");
        setKpis(data);
      } catch {
        setKpis(null);
      }
    })();
  }, []);

  return (
    <div className="border-b border-line bg-surface/50 px-5 py-3 sm:px-8 lg:px-10">
      <div className="mx-auto flex w-full max-w-[1400px] items-center gap-3">
        <div className="hidden shrink-0 items-center gap-2 pr-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-700 md:flex">
          <ShieldCheck className="h-4 w-4" />
          Co-evolution scoreboard
        </div>
        <div className="scroll-thin flex flex-1 items-stretch gap-2 overflow-x-auto">
          {CELLS.map((c) => {
            const Icon = c.icon;
            return (
              <div
                key={c.label}
                className="flex min-w-[150px] flex-1 items-center gap-3 rounded border border-line bg-surface/70 px-3 py-2"
              >
                <span className={`grid h-8 w-8 shrink-0 place-items-center rounded bg-subtle ${c.accent}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="flex flex-col">
                  <span className="text-[10px] font-medium uppercase tracking-wide text-ink-ghost">
                    {c.label}
                  </span>
                  <span className="font-mono text-sm font-bold tabular-nums text-ink">
                    {c.render(kpis)}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
