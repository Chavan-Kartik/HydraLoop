"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Bot, Play, ShieldAlert, Radar, Fingerprint } from "lucide-react";
import { getThreats, Threat, ThreatCatalog } from "@/lib/api";
import { Badge, ErrorBox, Card, Loading, OfflineBadge, SectionLabel } from "./ui";

type Status = "loading" | "ready" | "error";

const RISK_TONE: Record<string, string> = { high: "red", medium: "amber", low: "blue" };

export function ThreatBoard() {
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [data, setData] = useState<ThreatCatalog | null>(null);
  const [family, setFamily] = useState<string | null>(null);

  const [selected, setSelected] = useState<Threat | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { data, offline } = await getThreats();
        setData(data);
        setOffline(offline);
        setStatus("ready");
      } catch (e) {
        setError((e as Error).message);
        setStatus("error");
      }
    })();
  }, []);

  const shown = useMemo(
    () => (data ? data.threats.filter((t) => !family || t.family === family) : []),
    [data, family],
  );

  if (status === "loading") return <Loading label="threat catalog" />;
  if (status === "error") return <ErrorBox message={error} />;
  if (!data) return null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {offline && <OfflineBadge />}
        <Chip label={`All (${data.total})`} active={!family} onClick={() => setFamily(null)} />
        {data.families.map((f) => (
          <Chip
            key={f.family}
            label={`${f.label} (${f.count})`}
            active={family === f.family}
            highlight={f.family === "agentic_commerce"}
            onClick={() => setFamily(f.family)}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {shown.map((t, i) => (
          <motion.div
            key={t.attack_id}
            layout
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: Math.min(i * 0.03, 0.3) }}
          >
            <ThreatCard t={t} active={selected?.attack_id === t.attack_id} onSelect={() => setSelected(t)} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function Chip({
  label,
  active,
  highlight,
  onClick,
}: {
  label: string;
  active: boolean;
  highlight?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all ${
        active
          ? "bg-accent-600 text-white shadow-card"
          : highlight
            ? "border border-accent-200 bg-accent-50 text-accent-700"
            : "border border-line bg-surface text-ink-faint hover:border-accent-200 hover:text-ink"
      }`}
    >
      {highlight && <Bot className="h-3.5 w-3.5" />}
      {label}
    </button>
  );
}

function labPrompt(t: Threat) {
  const family = t.family.replace(/_/g, " ");
  return (
    `${t.attack_name} is a ${family} pattern. ` +
    `Behavioural signals: ${t.behavioral_signals.join(", ")}. ` +
    `Payment surfaces: ${t.payment_surface.join(", ")}.`);
}

function ThreatCard({ t, active, onSelect }: { t: Threat; active: boolean; onSelect: () => void }) {
  const agentic = t.family === "agentic_commerce";
  const href = `/?run=1&text=${encodeURIComponent(labPrompt(t))}`;
  return (
    <Card className={`h-full p-5 ${agentic ? "ring-1 ring-accent-200" : ""} ${active ? "ring-2 ring-navy" : ""}`}>
      <button type="button" onClick={onSelect} className="w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span
              className={`grid h-9 w-9 shrink-0 place-items-center rounded ${
                agentic ? "bg-accent-600 text-white" : "bg-subtle text-ink-faint"
              }`}
            >
              {agentic ? <Bot className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
            </span>
            <div>
              <div className="font-mono text-[11px] font-semibold text-ink-ghost">{t.attack_id}</div>
              <div className="text-sm font-bold leading-tight text-ink">{t.attack_name}</div>
            </div>
          </div>
          <Badge tone={RISK_TONE[t.risk_level] ?? "slate"}>{t.risk_level}</Badge>
        </div>
      </button>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge tone="slate">{t.family_label}</Badge>
        {t.evolvable && <Badge tone="brand">evolvable</Badge>}
        <span className="chip">
          <Fingerprint className="h-3 w-3" /> metadata-only
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <div>
          <div className="mb-1 flex items-center gap-1.5">
            <Radar className="h-3.5 w-3.5 text-accent-700" />
            <SectionLabel>signals</SectionLabel>
          </div>
          <div className="flex flex-wrap gap-1">
            {t.behavioral_signals.map((s) => (
              <span
                key={s}
                className="rounded-md bg-subtle px-2 py-0.5 font-mono text-[10px] text-ink-soft"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <div>
          <SectionLabel>mitigations</SectionLabel>
          <div className="mt-1 text-xs text-ink-faint">{t.mitigation_options.join(", ")}</div>
        </div>
        <Link
          href={href}
          className="relative mt-1 inline-flex w-full items-center justify-center gap-2 rounded bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white shadow-card"
        >
          <Play className="h-3.5 w-3.5" />
          Run this in the lab
        </Link>
      </div>
    </Card>
  );
}
