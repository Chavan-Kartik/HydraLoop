"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getRuns, getScoreboard, Scoreboard as ScoreData } from "@/lib/api";
import { Empty, ErrorBox, Loading, OfflineBadge, Panel } from "./StateBlocks";

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
      <Panel title="Escape rate and archive recall by generation">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.points} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis dataKey="generation" stroke="#64748b" />
            <YAxis stroke="#64748b" domain={[0, 1]} />
            <Tooltip contentStyle={{ background: "#0b0e14", border: "1px solid #1e293b" }} />
            <Legend />
            <ReferenceLine
              y={FRICTION_GUARDRAIL}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: "friction budget", fill: "#f59e0b", fontSize: 10 }}
            />
            <Line type="monotone" dataKey="escape_rate" stroke="#ff5c7a" strokeWidth={2} />
            <Line
              type="monotone"
              dataKey="candidate_archive_recall"
              stroke="#4cc9f0"
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="incumbent_archive_recall"
              stroke="#8892b0"
              strokeDasharray="4 4"
            />
          </LineChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Regression gauntlet log">
        <ul className="space-y-1 text-sm">
          {data.gauntlet_log.map((g, i) => (
            <li key={i} className="flex gap-3">
              <span className="text-slate-600">G{g.generation}</span>
              <span className={g.promoted ? "text-blue" : "text-red"}>
                {g.promoted ? "PROMOTE" : "REJECT"}
              </span>
              <span className="text-slate-400">{g.result}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
