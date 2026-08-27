"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CheckCircle2, XCircle } from "lucide-react";
import { getRuns, getScoreboard, Scoreboard as ScoreData } from "@/lib/api";
import { Badge, Empty, ErrorBox, Loading, OfflineBadge, Panel, SectionLabel } from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

const SERIES = [
  {
    key: "escape rate",
    colour: "#f43f5e",
    text: "Share of this generation's attack transactions the live defence approved. Lower is better. It starts at or near 1.0, because generation 1 has no trained model to beat yet.",
  },
  {
    key: "candidate recall",
    colour: "#4f46e5",
    text: "How much of the archive of older attacks the newly retrained model still catches. This is the number the gauntlet gates on.",
  },
  {
    key: "incumbent recall",
    colour: "#94a3b8",
    text: "The same measure for the model currently deployed. A candidate below this line has forgotten something, and gets rolled back.",
  },
];

export function Scoreboard() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [data, setData] = useState<ScoreData | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const runs = await getRuns();
      setOffline(runs.offline);
      const rid = runs.data.runs?.[0]?.run_id;
      if (!rid) {
        setStatus("empty");
        return;
      }
      const sb = await getScoreboard(rid);
      setOffline(sb.offline);
      setData(sb.data);
      setStatus(sb.data.points.length ? "ready" : "empty");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (status === "loading") return <Loading label="scoreboard" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (status === "empty" || !data) return <Empty label="metrics" />;

  return (
    <div className="space-y-4">
      {offline && <OfflineBadge />}
      <Panel title="Escape rate and archive recall, by generation">
        <p className="mb-3 text-xs leading-relaxed text-ink-faint">
          One point per generation of the co-evolution loop. All three series are fractions on
          the same 0 to 1 axis. The loop is working when the red area falls while the two recall
          lines stay level, meaning the defence closed the new escape route without losing the
          attacks it already handled.
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data.points} margin={{ top: 10, right: 16, bottom: 4, left: -8 }}>
            <defs>
              <linearGradient id="escapeFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.28} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e3e7f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="generation"
              stroke="#94a3b8"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "#e3e7f0" }}
            />
            <YAxis
              stroke="#94a3b8"
              domain={[0, 1]}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#ffffff",
                border: "1px solid #e3e7f0",
                borderRadius: 12,
                boxShadow: "0 8px 24px -12px rgba(16,24,40,0.18)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area
              type="monotone"
              name="escape rate"
              dataKey="escape_rate"
              stroke="#f43f5e"
              strokeWidth={2.5}
              fill="url(#escapeFill)"
            />
            <Line
              type="monotone"
              name="candidate recall"
              dataKey="candidate_archive_recall"
              stroke="#4f46e5"
              strokeWidth={2.5}
              dot={false}
            />
            <Line
              type="monotone"
              name="incumbent recall"
              dataKey="incumbent_archive_recall"
              stroke="#94a3b8"
              strokeDasharray="5 4"
              strokeWidth={1.5}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>

        <div className="mt-3 space-y-2 border-t border-line pt-3">
          <SectionLabel>what each line means</SectionLabel>
          {SERIES.map((s) => (
            <div key={s.key} className="flex gap-2.5 text-xs leading-relaxed">
              <span
                className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                style={{ background: s.colour }}
              />
              <span className="text-ink-faint">
                <span className="font-semibold text-ink-soft">{s.key}.</span> {s.text}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Regression gauntlet log">
        <p className="mb-3 text-xs leading-relaxed text-ink-faint">
          Every promotion decision, in order. A candidate is only allowed to replace the live
          model if it holds its recall on the archive of older attacks, so a{" "}
          <span className="font-semibold text-ink-soft">reject</span> here is the gate doing its
          job rather than a failure. The reason string carries the recall it regressed from and
          to, and the tolerance it had to stay within.
        </p>
        <ul className="space-y-1.5">
          {data.gauntlet_log.map((g, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded border border-line bg-surface/60 px-3 py-2 text-sm"
            >
              <span className="font-mono text-[10px] font-semibold text-ink-ghost">G{g.generation}</span>
              {g.promoted ? (
                <Badge tone="blue">
                  <CheckCircle2 className="h-3 w-3" /> promote
                </Badge>
              ) : (
                <Badge tone="red">
                  <XCircle className="h-3 w-3" /> reject
                </Badge>
              )}
              <span className="text-ink-faint">{g.result}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
