"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  RotateCw,
  Presentation,
  ChevronLeft,
  ChevronRight,
  Swords,
  Flame,
  ArrowUpCircle,
  Radio,
} from "lucide-react";
import {
  API_BASE,
  ArenaEvent,
  arenaSocketUrl,
  getArena,
  getRuns,
} from "@/lib/api";
import {
  Figure,
  Badge,
  Empty,
  ErrorBox,
  GhostButton,
  Card,
  PrimaryButton,
  Loading,
  OfflineBadge,
  Panel,
  SectionLabel,
} from "./ui";
import { LoopDiagram } from "./LoopDiagram";
import { StrategistBeat, VerbStrip } from "./Brief";

type Beat = { title: string; detail: string };

function buildNarrative(events: ArenaEvent[]): Beat[] {
  const beats: Beat[] = [
    {
      title: "The premise",
      detail:
        "Autonomous agents now initiate payments. Fraud becomes an adaptive adversary, so we breed attacks and harden defenses in a closed loop.",
    },
  ];
  const generations = [...new Set(events.map((e) => e.generation))].sort((a, b) => a - b);
  for (const g of generations) {
    const summary = events.find((e) => e.generation === g && e.type === "generation_summary");
    const escapes = events.filter((e) => e.generation === g && e.type === "escape");
    const rejects = events.filter(
      (e) => e.generation === g && e.type === "gauntlet" && String(e.text).startsWith("REJECT"),
    );
    const rate = summary ? Number(summary.data.escape_rate ?? 0) : 0;
    const promoted = summary ? Boolean(summary.data.promoted) : false;
    const escapeModes = escapes.map((e) => e.data.dominant_attack_id).filter(Boolean);
    beats.push({
      title: `Generation ${g}: escape rate ${(rate * 100).toFixed(0)}%`,
      detail:
        (escapeModes.length
          ? `Red team escapes via ${[...new Set(escapeModes)].join(", ")}. `: "Red team finds no new way through. ") +
        (rejects.length
          ? `The gauntlet blocks a regressive model (rollback protects the incumbent). `: promoted
            ? `A stronger detector clears the gauntlet and is promoted. `: ""),
    });
  }
  beats.push({
    title: "The takeaway",
    detail:
      "As the loop runs, escape rate and attacker ROI collapse together while every decision stays on a tamper-evident audit trail.",
  });
  return beats;
}

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
  const [demoStep, setDemoStep] = useState<number | null>(null);
  const [playback, setPlayback] = useState<"idle" | "live" | "computing">("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const lastSeq = useRef(-1);
  const localTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const narrative = useMemo(() => buildNarrative(events), [events]);

  const stopPlayback = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    if (localTimer.current) {
      clearInterval(localTimer.current);
      localTimer.current = null;
    }
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setStreaming(false);
  }, []);

  useEffect(() => {
    if (demoStep === null) return;
    if (demoStep >= narrative.length - 1) return;
    const t = setTimeout(() => setDemoStep((s) => (s === null ? null : s + 1)), 4000);
    return () => clearTimeout(t);
  }, [demoStep, narrative.length]);

  const playLocal = useCallback((all: ArenaEvent[]) => {
    stopPlayback();
    setEvents([]);
    setPlayback("live");
    setStreaming(true);
    let i = 0;
    localTimer.current = setInterval(() => {
      if (i >= all.length) {
        if (localTimer.current) clearInterval(localTimer.current);
        localTimer.current = null;
        setStreaming(false);
        setPlayback("idle");
        return;
      }
      const ev = all[i];
      i += 1;
      setEvents((prev) => [...prev, ev]);
    }, 280);
  }, [stopPlayback]);

  const stream = useCallback(
    (rid: string, resume: boolean) => {
      stopPlayback();
      if (!resume) {
        setEvents([]);
        lastSeq.current = -1;
      }
      const ws = new WebSocket(arenaSocketUrl(rid, resume ? lastSeq.current : -1, 280));
      wsRef.current = ws;
      setStreaming(true);
      setPlayback("live");
      ws.onmessage = (m) => {
        const msg = JSON.parse(m.data);
        if (msg.type === "resync") {
          setDropped((d) => d + msg.dropped);
          return;
        }
        if (msg.type === "complete") {
          setStreaming(false);
          setPlayback("idle");
          return;
        }
        lastSeq.current = msg.seq;
        setEvents((prev) => [...prev, msg]);
      };
      ws.onerror = () => {
        setStreaming(false);
        setPlayback("idle");
      };
      ws.onclose = () => {
        setStreaming(false);
      };
    },
    [stopPlayback],
  );

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
      setStatus("ready");
      if (arena.offline) {
        playLocal(arena.data.events);
      } else {
        stream(rid, false);
      }
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }, [playLocal, stream]);

  useEffect(() => {
    loadLatestRun();
    return () => stopPlayback();
  }, [loadLatestRun, stopPlayback]);

  const runCoevolution = useCallback(async () => {
    setRunning(true);
    setPlayback("computing");
    setError("");
    setEvents([]);
    stopPlayback();
    try {
      const res = await fetch(`${API_BASE}/api/run?generations=3`, { method: "POST" });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      const rid = body.run_id as string;
      setRunId(rid);
      setOffline(false);
      setStatus("ready");
      pollTimer.current = setInterval(async () => {
        try {
          const st = await fetch(`${API_BASE}/api/run/${rid}`, { cache: "no-store" });
          const job = await st.json();
          if (job.status === "done") {
            if (pollTimer.current) clearInterval(pollTimer.current);
            pollTimer.current = null;
            setRunning(false);
            stream(rid, false);
          } else if (job.status === "error") {
            if (pollTimer.current) clearInterval(pollTimer.current);
            pollTimer.current = null;
            setRunning(false);
            setPlayback("idle");
            setError(job.error || "loop failed");
            setStatus("error");
          }
        } catch {
          /* keep polling while the API is busy */
        }
      }, 1000);
    } catch (e) {
      setRunning(false);
      setPlayback("idle");
      setError((e as Error).message);
      setStatus("error");
    }
  }, [stopPlayback, stream]);

  if (status === "loading") return <Loading label="arena" />;
  if (status === "error") return <ErrorBox message={error} />;

  const escapes = events.filter((e) => e.type === "escape").length;
  const promotions = events.filter((e) => e.type === "generation_summary" && e.data.promoted).length;
  const generation = events.reduce((m, e) => Math.max(m, e.generation), 0);
  const live = streaming || playback === "live" || playback === "computing";

  return (
    <div className="space-y-6">
      <VerbStrip />

      {/* Hero */}
      <Card className="overflow-hidden p-0">
        <div className="grid gap-6 p-6 lg:grid-cols-[1.05fr_1fr] lg:p-8">
          <div className="flex flex-col justify-center">
            <div className="mb-3 inline-flex w-fit items-center gap-2 rounded-full border border-line bg-surface/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-700">
              <Swords className="h-3.5 w-3.5" /> Agentic-commerce defense
            </div>
            <h1 className="text-xl font-bold leading-tight tracking-tight text-ink sm:text-4xl">
              We don&apos;t just detect fraud.
              <br />
              We make the attack <span className="text-accent-700">uneconomic</span>.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-faint">
              Watch the red and blue logs below. They fill as the loop runs. Then click
              <span className="font-semibold text-ink"> Start live loop</span> to compute a new
              3-generation run (API must be on; takes about 30 to 60 seconds).
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <PrimaryButton onClick={runCoevolution} disabled={running || playback === "computing"}>
                <Play className="h-4 w-4" />
                {running || playback === "computing"
                  ? "Computing loop"
                  : streaming
                    ? "Streaming"
                    : "Start live loop"}
              </PrimaryButton>
              {runId && (
                <GhostButton onClick={() => runId && stream(runId, false)} disabled={streaming}>
                  <RotateCw className="h-4 w-4" /> Replay
                </GhostButton>
              )}
              <GhostButton
                active={demoStep !== null}
                onClick={() => setDemoStep(demoStep === null ? 0 : null)}
              >
                <Presentation className="h-4 w-4" />
                {demoStep === null ? "Caption walkthrough" : "Exit captions"}
              </GhostButton>
              {playback === "computing" && (
                <span className="text-xs font-semibold text-ink-soft">
                  Twin and detector running. Logs will stream when generation 1 lands.
                </span>
              )}
              {live && playback !== "computing" && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red">
                  <Radio className="h-3.5 w-3.5 animate-pulse" /> LIVE
                </span>
              )}
              {offline && <OfflineBadge />}
              {dropped > 0 && <Badge tone="red">{dropped} events dropped</Badge>}
            </div>
          </div>

            <div className="rounded-md border border-line bg-subtle/40 p-4">
            <LoopDiagram active={live} />
          </div>
        </div>
      </Card>

      {/* Stat row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={<Swords className="h-5 w-5" />} label="Generation" value={generation} tone="brand" />
        <StatCard icon={<Flame className="h-5 w-5" />} label="Escapes" value={escapes} tone="red" />
        <StatCard icon={<ArrowUpCircle className="h-5 w-5" />} label="Promotions" value={promotions} tone="blue" />
      </div>

      {/* Demo narrative */}
      <AnimatePresence>
        {demoStep !== null && narrative[demoStep] && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-accent-200 bg-accent-50/60 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-bold text-accent-700">
                  <Presentation className="h-4 w-4" />
                  {narrative[demoStep].title}
                </div>
                <div className="flex items-center gap-2 text-xs text-ink-faint">
                  <button
                    onClick={() => setDemoStep((s) => Math.max(0, (s ?? 0) - 1))}
                    disabled={demoStep === 0}
                    className="grid h-6 w-6 place-items-center rounded-md border border-line bg-surface disabled:opacity-40"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </button>
                  <span className="font-mono tabular-nums">
                    {demoStep + 1}/{narrative.length}
                  </span>
                  <button
                    onClick={() => setDemoStep((s) => Math.min(narrative.length - 1, (s ?? 0) + 1))}
                    disabled={demoStep >= narrative.length - 1}
                    className="grid h-6 w-6 place-items-center rounded-md border border-line bg-surface disabled:opacity-40"
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                {narrative[demoStep].detail}
              </p>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <StrategistBeat />

      {/* Red vs Blue arena */}
      {status === "empty" ? (
        <Empty label="runs" />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel
            title="Red team escapes"
            right={<Badge tone="red">{escapes} found</Badge>}
          >
            <Ticker events={events.filter((e) => e.type === "escape")} tone="red" />
          </Panel>
          <Panel
            title="Blue team defense"
            right={<Badge tone="blue">{promotions} promoted</Badge>}
          >
            <Ticker
              events={events.filter(
                (e) => e.type === "gauntlet" || e.type === "generation_summary",
              )}
              tone="blue"
            />
          </Panel>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  tone: "red" | "blue" | "brand";
}) {
  const color =
    tone === "red" ? "text-red" : tone === "blue" ? "text-blue" : "text-accent-700";
  const bg =
    tone === "red" ? "bg-red/10" : tone === "blue" ? "bg-blue/10" : "bg-accent-50";
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <SectionLabel>{label}</SectionLabel>
        <span className={`grid h-9 w-9 place-items-center rounded ${bg} ${color}`}>{icon}</span>
      </div>
      <div className={`mt-2 font-mono text-4xl font-bold tabular-nums ${color}`}>
        <Figure value={value} />
      </div>
    </Card>
  );
}

function Ticker({ events, tone }: { events: ArenaEvent[]; tone: "red" | "blue" }) {
  const dot = tone === "red" ? "bg-red" : "bg-blue";
  const text = tone === "red" ? "text-red-ink" : "text-blue-ink";
  if (events.length === 0)
    return (
      <div className="flex h-24 items-center justify-center text-sm text-ink-ghost">
        waiting for events
      </div>
    );
  return (
    <ul className="scroll-thin max-h-96 space-y-1.5 overflow-y-auto pr-1">
      <AnimatePresence initial={false}>
        {events.map((e, i) => (
          <motion.li
            key={e.seq ?? i}
            layout
            initial={{ opacity: 0, x: tone === "red" ? -12 : 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-start gap-2.5 rounded border border-line bg-surface/60 px-3 py-2 text-sm"
          >
            <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
            <span className="shrink-0 font-mono text-[10px] font-semibold text-ink-ghost">
              G{e.generation}
            </span>
            <span className={`leading-snug ${text}`}>{e.text}</span>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}
