"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_BASE,
  ArenaEvent,
  arenaSocketUrl,
  getArena,
  getRuns,
} from "@/lib/api";
import { Empty, ErrorBox, Loading, OfflineBadge, Panel } from "./StateBlocks";

type Status = "loading" | "ready" | "empty" | "error";

export function Arena() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<ArenaEvent[]>([]);
  const [dropped, setDropped] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [running, setRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const lastSeq = useRef(-1);

  const loadLatestRun = useCallback(async () => {
    setStatus("loading");
    try {
      const { data, offline } = await getRuns();
      setOffline(offline);
      const rid = data.runs?.[0]?.run_id ?? null;
      if (!rid) {
        setStatus("empty");
        return;
      }
      setRunId(rid);
      const arena = await getArena(rid);
      setOffline(arena.offline);
      setEvents(arena.data.events);
      lastSeq.current = arena.data.events.length - 1;
      setStatus("ready");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    loadLatestRun();
    return () => wsRef.current?.close();
  }, [loadLatestRun]);

  const stream = useCallback(
    (rid: string, resume: boolean) => {
      wsRef.current?.close();
      if (!resume) {
        setEvents([]);
        lastSeq.current = -1;
      }
      const ws = new WebSocket(arenaSocketUrl(rid, resume ? lastSeq.current : -1, 350));
      wsRef.current = ws;
      setStreaming(true);
      ws.onmessage = (m) => {
        const msg = JSON.parse(m.data);
        if (msg.type === "resync") {
          setDropped((d) => d + msg.dropped);
          return;
        }
        if (msg.type === "complete") {
          setStreaming(false);
          return;
        }
        lastSeq.current = msg.seq;
        setEvents((prev) => [...prev, msg]);
      };
      ws.onerror = () => setStreaming(false);
      ws.onclose = () => setStreaming(false);
    },
    [],
  );

  const runCoevolution = useCallback(async () => {
    setRunning(true);
    try {
      const res = await fetch(`${API_BASE}/api/run?generations=5`, { method: "POST" });
      const body = await res.json();
      setRunId(body.run_id);
      stream(body.run_id, false);
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    } finally {
      setRunning(false);
    }
  }, [stream]);

  if (status === "loading") return <Loading label="arena" />;
  if (status === "error") return <ErrorBox message={error} />;

  const escapes = events.filter((e) => e.type === "escape").length;
  const promotions = events.filter(
    (e) => e.type === "generation_summary" && e.data.promoted,
  ).length;
  const generation = events.reduce((m, e) => Math.max(m, e.generation), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={runCoevolution}
          disabled={running || streaming}
          className="rounded bg-blue px-5 py-2 font-bold text-ink disabled:opacity-40"
        >
          {running ? "STARTING..." : streaming ? "STREAMING..." : "RUN CO-EVOLUTION"}
        </button>
        {runId && (
          <button
            onClick={() => runId && stream(runId, false)}
            disabled={streaming}
            className="rounded border border-slate-700 px-4 py-2 text-sm disabled:opacity-40"
          >
            Replay
          </button>
        )}
        {offline && <OfflineBadge />}
        {dropped > 0 && (
          <span className="rounded bg-red/20 px-2 py-0.5 text-xs text-red">
            {dropped} events dropped
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Counter label="Generation" value={generation} tone="text-slate-200" />
        <Counter label="Escapes" value={escapes} tone="text-red" />
        <Counter label="Promotions" value={promotions} tone="text-blue" />
      </div>

      {status === "empty" ? (
        <Empty label="runs" />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Panel title="Red Team">
            <Ticker events={events.filter((e) => e.type === "escape")} tone="text-red" />
          </Panel>
          <Panel title="Blue Team">
            <Ticker
              events={events.filter((e) => e.type === "gauntlet" || e.type === "generation_summary")}
              tone="text-blue"
            />
          </Panel>
        </div>
      )}
    </div>
  );
}

function Counter({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-panel/70 p-4 text-center">
      <div className="text-xs uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-3xl font-bold ${tone}`}>{value}</div>
    </div>
  );
}

function Ticker({ events, tone }: { events: ArenaEvent[]; tone: string }) {
  if (events.length === 0) return <div className="text-slate-600">waiting for events...</div>;
  return (
    <ul className="max-h-80 space-y-1 overflow-y-auto text-sm">
      {events.map((e, i) => (
        <li key={i} className="flex gap-2">
          <span className="text-slate-600">G{e.generation}</span>
          <span className={tone}>{e.text}</span>
        </li>
      ))}
    </ul>
  );
}
