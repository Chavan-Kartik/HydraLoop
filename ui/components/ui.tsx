"use client";

/**
 * Shared primitives for the console.
 *
 * These deliberately do very little. An earlier version gave every card a
 * mouse-tracking spotlight, every button a gradient and a shimmer sweep, and
 * every figure a one-second count-up animation. In a fraud console that is
 * actively harmful: the count-up means a number is wrong while it animates, and
 * the decoration competes with the data for attention. What is left is flat
 * surfaces, one accent colour, and motion only where it carries information.
 */

import { motion } from "framer-motion";

/* -------------------------------------------------------------------------- */
/*  Surfaces                                                                   */
/* -------------------------------------------------------------------------- */

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`panel ${className}`}>{children}</div>;
}

export function Panel({
  title,
  children,
  right,
  className = "",
  bodyClassName = "p-3",
}: {
  title?: string;
  children: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <Card className={className}>
      {(title || right) && (
        <div className="panel-header">
          {title ? <span className="label">{title}</span> : <span />}
          {right}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/*  Buttons                                                                    */
/* -------------------------------------------------------------------------- */

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean;
};

export function PrimaryButton({ className = "", children, ...props }: BtnProps) {
  return (
    <button
      {...props}
      className={`focus-ring inline-flex items-center justify-center gap-1.5 rounded border border-accent-600 bg-accent-600 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-accent-700 disabled:pointer-events-none disabled:opacity-40 ${className}`}
    >
      {children}
    </button>
  );
}

export function GhostButton({ className = "", active, children, ...props }: BtnProps) {
  return (
    <button
      {...props}
      className={`focus-ring inline-flex items-center justify-center gap-1.5 rounded border px-2.5 py-1.5 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-40 ${
        active
          ? "border-accent-200 bg-accent-50 text-accent-700"
          : "border-line bg-surface text-ink-soft hover:bg-subtle hover:text-ink"
      } ${className}`}
    >
      {children}
    </button>
  );
}

/* -------------------------------------------------------------------------- */
/*  Badges and labels                                                          */
/* -------------------------------------------------------------------------- */

const TONES: Record<string, string> = {
  accent: "bg-accent-50 text-accent-700 border-accent-200",
  red: "bg-danger-50 text-danger-700 border-danger-200",
  blue: "bg-accent-50 text-accent-700 border-accent-200",
  amber: "bg-warn-50 text-warn-700 border-warn-200",
  green: "bg-success-50 text-success-700 border-success-200",
  slate: "bg-subtle text-ink-faint border-line",
};

export function Badge({
  tone = "slate",
  children,
  className = "",
}: {
  tone?: keyof typeof TONES | string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide ${
        TONES[tone] ?? TONES.slate
      } ${className}`}
    >
      {children}
    </span>
  );
}

/** Rightwards arrow. Escaped so the source stays ASCII. */
export const ARROW = "\u2192";

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="label">{children}</div>;
}

/**
 * A figure and its caption. Monospaced and tabular so columns of these line up
 * and do not jitter while a run streams.
 */
export function Metric({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "good" | "bad" | "warn";
}) {
  const toneClass = {
    default: "text-ink",
    good: "text-success-700",
    bad: "text-danger-700",
    warn: "text-warn-700",
  }[tone];
  return (
    <div className="min-w-0">
      <div className="label truncate">{label}</div>
      <div className={`mt-0.5 font-mono text-lg font-semibold tabular-nums ${toneClass}`}>
        {value}
      </div>
      {hint && <div className="mt-0.5 truncate text-2xs text-ink-ghost">{hint}</div>}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Motion                                                                     */
/* -------------------------------------------------------------------------- */

/** A short opacity fade. No translation, so nothing shifts under the cursor. */
export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.18, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/**
 * Renders a figure immediately.
 *
 * Kept as a component only so call sites do not have to change. It used to
 * animate from zero over about a second, which meant that for that second the
 * console displayed a number that was simply not the measurement.
 */
export function AnimatedNumber({
  value,
  format,
  className = "",
}: {
  value: number;
  format?: (n: number) => string;
  className?: string;
}) {
  return (
    <span className={`tabular-nums ${className}`}>
      {format ? format(value) : Math.round(value).toString()}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/*  Page header                                                                */
/* -------------------------------------------------------------------------- */

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  right,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-col gap-2 border-b border-line pb-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="label mb-1">{eyebrow}</div>}
        <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-ink-faint">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  State blocks                                                               */
/* -------------------------------------------------------------------------- */

export function Loading({ label }: { label: string }) {
  return (
    <div className="panel p-4">
      <div className="text-sm text-ink-faint">Loading {label}</div>
      <div className="mt-2 h-0.5 w-full overflow-hidden rounded bg-subtle">
        <div className="h-full w-1/4 animate-indeterminate rounded bg-accent-500" />
      </div>
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return (
    <div className="rounded-md border border-dashed border-line bg-surface p-8 text-center text-sm text-ink-faint">
      No {label} yet. Run a co-evolution to populate this view.
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
      Could not load data: {message}
    </div>
  );
}

export function OfflineBadge() {
  return <Badge tone="amber">offline, seeded snapshot</Badge>;
}
