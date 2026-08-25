"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CheckCircle2, XCircle } from "lucide-react";
import { getRuns, getScoreboard, Scoreboard as ScoreData } from "@/lib/api";
import { Badge, Empty, ErrorBox, Loading, OfflineBadge, Panel } from "./ui";

type Status = "loading" | "ready" | "empty" | "error";

const FRICTION_GUARDRAIL = 0.02;

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
      <Panel title="Escape rate & archive recall by generation">
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
            <ReferenceLine
              y={FRICTION_GUARDRAIL}
              stroke="#f59e0b"
              strokeDasharray="5 4"
              label={{ value: "friction budget", fill: "#b45309", fontSize: 10, position: "insideTopLeft" }}
            />
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
      </Panel>

      <Panel title="Regression gauntlet log">
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
