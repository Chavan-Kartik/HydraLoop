"use client";

import { Sword, Cpu, ShieldCheck } from "lucide-react";

/**
 * The closed loop, drawn.
 *
 * Red team evolves attacks, the twin executes them against the live policy, the
 * blue team scores and decides, and escapes feed back into retraining. The dash
 * only travels while a run is active, so the motion reports state rather than
 * decorating the page. Colour is by role, not by palette: attacker red, defender
 * blue, and a neutral slate for the twin, which belongs to neither side.
 */
export function LoopDiagram({ active }: { active?: boolean }) {
  const LOOP =
    "M140,130 C230,90 280,70 360,70 C440,70 490,90 580,130 C560,220 160,220 140,130";

  return (
    <div className="relative w-full" style={{ aspectRatio: "720 / 250" }}>
      <svg
        viewBox="0 0 720 250"
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
      >
        <path d={LOOP} fill="none" stroke="#e4e7ec" strokeWidth="8" strokeLinecap="round" />
        <path
          id="loop-path"
          d={LOOP}
          fill="none"
          stroke="#98a2b3"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray="5 9"
          className={active ? "animate-loop-dash" : ""}
        />
        {active && (
          <>
            <circle r="4" fill="#d92d20">
              <animateMotion dur="5.5s" repeatCount="indefinite" rotate="auto">
                <mpath href="#loop-path" />
              </animateMotion>
            </circle>
            <circle r="4" fill="#1d4ed8">
              <animateMotion dur="5.5s" begin="2.75s" repeatCount="indefinite" rotate="auto">
                <mpath href="#loop-path" />
              </animateMotion>
            </circle>
          </>
        )}
      </svg>

      <Node
        x="19.4%"
        y="52%"
        tone="red"
        icon={<Sword className="h-4 w-4" />}
        title="Red Team"
        sub="evolves attacks"
      />
      <Node
        x="50%"
        y="28%"
        tone="neutral"
        icon={<Cpu className="h-4 w-4" />}
        title="Payment Twin"
        sub="executes vs live policy"
      />
      <Node
        x="80.6%"
        y="52%"
        tone="blue"
        icon={<ShieldCheck className="h-4 w-4" />}
        title="Blue Team"
        sub="scores and decides"
      />

      <span
        className="absolute -translate-x-1/2 -translate-y-1/2 text-2xs font-medium uppercase tracking-wider text-ink-ghost"
        style={{ left: "50%", top: "86%" }}
      >
        {"escaped fraud \u2192 immune memory \u2192 retrain \u2192 gauntlet"}
      </span>
    </div>
  );
}

function Node({
  x,
  y,
  tone,
  icon,
  title,
  sub,
}: {
  x: string;
  y: string;
  tone: "red" | "blue" | "neutral";
  icon: React.ReactNode;
  title: string;
  sub: string;
}) {
  const fill = {
    red: "bg-danger-500",
    blue: "bg-accent-600",
    neutral: "bg-ink-soft",
  }[tone];
  return (
    <div
      className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
      style={{ left: x, top: y }}
    >
      <span className={`grid h-10 w-10 place-items-center rounded ${fill} text-white`}>
        {icon}
      </span>
      <span className="mt-1.5 rounded border border-line bg-surface px-2 py-0.5 text-center shadow-card">
        <span className="block text-xs font-semibold text-ink">{title}</span>
        <span className="block text-2xs text-ink-ghost">{sub}</span>
      </span>
    </div>
  );
}
