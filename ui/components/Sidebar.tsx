"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  Activity,
  FlaskConical,
  GitBranch,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Swords,
  type LucideIcon,
} from "lucide-react";

type Item = { href: string; label: string; icon: LucideIcon; hint: string };

const NAV: Item[] = [
  { href: "/", label: "Lab", icon: FlaskConical, hint: "Type a threat, watch every step" },
  { href: "/arena", label: "Arena", icon: Swords, hint: "Multi-generation loop replay" },
  { href: "/threats", label: "Threats", icon: ShieldAlert, hint: "Catalog of 28 scenarios" },
  { href: "/lineage", label: "Lineage", icon: GitBranch, hint: "Genome mutation trail" },
  { href: "/investigations", label: "Cases", icon: ScanSearch, hint: "SHAP investigations" },
  { href: "/scoreboard", label: "Metrics", icon: Activity, hint: "Escape rate by generation" },
  { href: "/governance", label: "Audit", icon: ShieldCheck, hint: "Hash-chained ledger" },
];

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="relative grid h-10 w-10 place-items-center rounded bg-accent-600 text-white shadow-card">
        <Swords className="h-5 w-5" />
        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-success-500 ring-2 ring-white" />
      </span>
      <span className="leading-tight">
        <span className="block text-base font-bold tracking-tight text-ink">
          Hydra<span className="text-accent-700">Loop</span>
        </span>
        <span className="block text-[10px] font-medium uppercase tracking-[0.2em] text-ink-ghost">
          Adversarial Lab
        </span>
      </span>
    </Link>
  );
}

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-[264px] shrink-0 flex-col border-r border-line bg-surface/70 px-4 py-6 lg:flex">
      <div className="px-2">
        <Brand />
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-1">
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-ink-ghost">
          Command Center
        </div>
        {NAV.map((item) => {
          const active = path === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="group relative flex items-center gap-3 rounded px-3 py-2.5 text-sm transition-colors"
            >
              {active && (
                <motion.span
                  layoutId="nav-active"
                  className="absolute inset-0 rounded border border-accent-200 bg-accent-50"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span
                className={`relative grid h-8 w-8 place-items-center rounded transition-colors ${
                  active
                    ? "bg-accent-600 text-white"
                    : "bg-subtle text-ink-faint group-hover:text-accent-700"
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              <span className="relative flex flex-col">
                <span
                  className={`font-semibold ${active ? "text-accent-700" : "text-ink-soft group-hover:text-ink"}`}
                >
                  {item.label}
                </span>
                <span className="text-[10px] text-ink-ghost">{item.hint}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 rounded border border-line bg-subtle/60 p-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold text-ink-soft">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success-500 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success-500" />
          </span>
          Loop online
        </div>
        <p className="mt-1 text-[10px] leading-relaxed text-ink-ghost">
          Synthetic, sandboxed, no PII, no cloud API key. Every decision on a
          tamper-evident trail.
        </p>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const path = usePathname();
  return (
    <div className="sticky top-0 z-20 border-b border-line bg-surface/80 lg:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <Brand />
      </div>
      <nav className="scroll-thin flex gap-1 overflow-x-auto px-3 pb-3">
        {NAV.map((item) => {
          const active = path === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex shrink-0 items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-accent-600 text-white"
                  : "border border-line bg-surface text-ink-faint"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
