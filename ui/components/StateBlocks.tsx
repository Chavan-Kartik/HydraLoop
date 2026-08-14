export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-panel/70 p-4">
      <h2 className="mb-3 text-xs uppercase tracking-widest text-slate-400">{title}</h2>
      {children}
    </section>
  );
}

export function Loading({ label }: { label: string }) {
  return <div className="animate-pulse text-slate-500">Loading {label}...</div>;
}

export function Empty({ label }: { label: string }) {
  return (
    <div className="rounded border border-dashed border-slate-700 p-6 text-center text-slate-500">
      No {label} yet. Run a co-evolution to populate this view.
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded border border-red/40 bg-red/10 p-4 text-red">
      Could not load data: {message}
    </div>
  );
}

export function OfflineBadge() {
  return (
    <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300">
      offline: showing pre-seeded snapshot
    </span>
  );
}
