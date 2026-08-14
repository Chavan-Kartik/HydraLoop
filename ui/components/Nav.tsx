"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Arena" },
  { href: "/scoreboard", label: "Scoreboard" },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
      <div className="text-lg font-bold tracking-widest text-slate-100">
        HYDRA<span className="text-blue">LOOP</span>
      </div>
      <nav className="flex gap-2">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded px-3 py-1 text-sm ${
              path === l.href ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
