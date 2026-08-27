export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export type ArenaEvent = {
  seq?: number;
  type: string;
  generation: number;
  text: string;
  data: Record<string, unknown>;
};

export type ScorePoint = {
  generation: number;
  escape_rate: number;
  escapes: number;
  candidate_archive_recall: number;
  incumbent_archive_recall: number;
  promoted: boolean;
};

export type Scoreboard = {
  run_id: string;
  points: ScorePoint[];
  gauntlet_log: { generation: number; candidate: string; result: string; promoted: boolean }[];
};

/**
 * Fetch from the live API, falling back to the bundled snapshot under /seed
 * so the command center still renders when the venue wifi is dead.
 */
async function fetchWithSeed<T>(apiPath: string, seedPath: string): Promise<{ data: T; offline: boolean }> {
  try {
    const res = await fetch(`${API_BASE}${apiPath}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`status ${res.status}`);
    return { data: (await res.json()) as T, offline: false };
  } catch {
    const res = await fetch(seedPath, { cache: "no-store" });
    return { data: (await res.json()) as T, offline: true };
  }
}

export async function getRuns() {
  return fetchWithSeed<{ runs: { run_id: string; generations: number }[] }>(
    "/api/runs",
    "/seed/runs.json",
  );
}

export async function getArena(runId: string) {
  return fetchWithSeed<{ run_id: string; events: ArenaEvent[] }>(
    `/api/arena/${runId}`,
    "/seed/arena.json",
  );
}

export async function getScoreboard(runId: string) {
  return fetchWithSeed<Scoreboard>(`/api/scoreboard/${runId}`, "/seed/scoreboard.json");
}

export function arenaSocketUrl(runId: string, since: number, tickMs: number): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/arena/${runId}?since=${since}&tick_ms=${tickMs}`;
}

// --- Expanded command center ------------------------------------------------

export type Threat = {
  attack_id: string;
  attack_name: string;
  family: string;
  family_label: string;
  risk_level: string;
  evolvable: boolean;
  validation_status: string;
  abstraction_level: string;
  payment_surface: string[];
  behavioral_signals: string[];
  mitigation_options: string[];
};

export type ThreatCatalog = {
  threats: Threat[];
  families: { family: string; label: string; count: number }[];
  total: number;
};

export type LineageNode = {
  id: string;
  generation: number;
  genome_id: string;
  attack_id: string;
  family: string;
  size: number;
  brief: string;
};

export type Lineage = {
  run_id: string;
  nodes: LineageNode[];
  edges: { from: string; to: string; attack_id: string }[];
  genomes: { attack_id: string; family: string; brief: string }[];
};

export type ReasonCode = { feature: string; contribution: number };

export type InvestigationCase = {
  txn_id: string;
  risk_score: number;
  is_fraud: boolean;
  reason_codes: ReasonCode[];
  // Null when the explainer could not run for this row. The alternative, filling
  // in plausible numbers, would be indistinguishable from a real explanation.
  counterfactual: {
    feature: string;
    from_value: number;
    to_value: number;
    risk_before: number;
    risk_after: number;
  } | null;
};

export type Investigations = { run_id: string; cases: InvestigationCase[] };

export type GovernanceEntry = {
  generation: number;
  entry_hash: string;
  prev_hash: string;
  promoted: boolean;
  escape_rate: number;
  config_hash: string;
  link_ok: boolean;
  /** Exact bytes the digest covers, so the browser can recompute it. */
  canonical?: string;
};

export type Governance = {
  run_id: string;
  verified: boolean;
  break_at: number | null;
  head_hash: string;
  length: number;
  algorithm?: string;
  genesis?: string;
  entries: GovernanceEntry[];
};

export type Kpis = {
  run_id: string;
  generations: number;
  escape_rate_start?: number;
  escape_rate_end?: number;
  promotions?: number;
  rollbacks?: number;
  total_escapes?: number;
  best_archive_recall?: number;
  attacker_roi_start?: number;
  attacker_roi_end?: number;
  behavior_coverage_end?: number;
  roi_collapsed?: boolean;
};

export async function latestRunId(): Promise<{ runId: string | null; offline: boolean }> {
  const { data, offline } = await getRuns();
  return { runId: data.runs?.[0]?.run_id ?? null, offline };
}

export async function getThreats() {
  return fetchWithSeed<ThreatCatalog>("/api/threats", "/seed/threats.json");
}

export async function getLineage(runId: string) {
  return fetchWithSeed<Lineage>(`/api/lineage/${runId}`, "/seed/lineage.json");
}

export async function getInvestigations(runId: string) {
  return fetchWithSeed<Investigations>(
    `/api/investigations/${runId}`,
    "/seed/investigations.json",
  );
}

export async function getGovernance(runId: string) {
  return fetchWithSeed<Governance>(`/api/governance/${runId}`, "/seed/governance.json");
}

export async function getKpis(runId: string) {
  return fetchWithSeed<Kpis>(`/api/kpis/${runId}`, "/seed/kpis.json");
}

export type StrategistPipelineStep = {
  verb: string;
  title: string;
  detail: string;
  href: string;
};

export type Strategist = {
  run_id: string;
  provider: string;
  model: string | null;
  available: boolean;
  proposals: number;
  accepted: number;
  refused: number;
  llm_authored: number;
  samples: { genome_id: string; family: string; reason: string; brief: string }[];
  requires_api_key: boolean;
  default_mode: string;
  optional_provider: string;
  guardrail: string;
  pipeline: StrategistPipelineStep[];
  source?: string;
};

export async function getStrategist(runId: string) {
  return fetchWithSeed<Strategist>(`/api/strategist/${runId}`, "/seed/strategist.json");
}

export type LabStep = { id: string; title: string; ok: boolean; detail: string };

export type LabHighlight = { label: string; value: string };

export type LabCase = InvestigationCase & { amount_minor?: number; action?: string };

export type LabResult = {
  family: string;
  attack_name: string;
  method: string;
  genome_id: string;
  brief: string;
  signals: string[];
  highlights?: LabHighlight[];
  steps: LabStep[];
  stats: {
    n_txns: number;
    n_fraud: number;
    n_legit: number;
    caught?: number;
    escaped?: number;
    false_positives?: number;
  };
  cases: LabCase[];
  txns: {
    txn_id: string;
    is_fraud: boolean;
    amount_minor: number;
    risk_score: number;
    action: string;
    channel?: string;
  }[];
};

export type LabEvent =
  | { type: "status"; phase: string; message: string }
  | { type: "step"; step: LabStep }
  | { type: "identity"; family: string; attack_name: string; method: string; signals: string[]; genome_id: string }
  | { type: "genome"; brief: string; highlights: LabHighlight[] }
  | { type: "sim"; n_txns: number; n_fraud: number; n_legit: number }
  | { type: "scores"; stats: LabResult["stats"]; txns: LabResult["txns"] }
  | { type: "cases"; cases: LabCase[] }
  | { type: "done"; result: LabResult }
  | { type: "error"; detail: string };

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function runLab(text: string): Promise<LabResult> {
  const res = await fetch(`${API_BASE}/api/lab`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err.slice(0, 200) || `lab failed (${res.status})`);
  }
  return res.json() as Promise<LabResult>;
}

export async function getLabLatest(): Promise<LabResult | null> {
  try {
    const res = await fetch(`${API_BASE}/api/lab/latest`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as LabResult;
  } catch {
    return null;
  }
}

/** Stream Identify to Detect. Falls back to a blocking POST if the stream route is missing. */
export async function streamLab(
  text: string,
  onEvent: (ev: LabEvent) => void,
  signal?: AbortSignal,
): Promise<LabResult> {
  const res = await fetch(`${API_BASE}/api/lab/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (res.status === 404 || !res.body) {
    const data = await runLab(text);
    for (const step of data.steps) {
      onEvent({ type: "step", step });
      await sleep(220);
    }
    onEvent({ type: "done", result: data });
    return data;
  }
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err.slice(0, 200) || `lab failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let result: LabResult | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const ev = JSON.parse(line) as LabEvent;
      onEvent(ev);
      if (ev.type === "error") throw new Error(ev.detail);
      if (ev.type === "done") result = ev.result;
    }
  }
  if (!result) throw new Error("lab stream ended without a result. Is the API up to date?");
  return result;
}

/* -------------------------------------------------------------------------- */
/*  Harden: the closed loop on demand                                         */
/* -------------------------------------------------------------------------- */

export type HardenSide = {
  recall: number;
  caught: number;
  escaped: number;
  false_positives: number;
  fpr: number;
  escaped_value_minor: number;
  threshold: number;
};

export type HardenTxn = {
  txn_id: string;
  amount_minor: number;
  before: number;
  after: number;
  caught_before: boolean;
  caught_after: boolean;
};

export type HardenGauntlet = {
  promote: boolean;
  reason: string;
  incumbent_recall: number;
  candidate_recall: number;
  candidate_fpr: number;
  candidate_ece: number;
};

export type HardenResult = {
  family: string;
  attack_name: string;
  genome_id: string;
  brief: string;
  promoted: boolean;
  gauntlet_reason: string;
  wave1: { n_fraud: number; escaped: number; recall: number };
  before: HardenSide;
  after: HardenSide;
  n_fraud: number;
  n_legit: number;
  newly_caught: number;
  value_recovered_minor: number;
  txns: HardenTxn[];
  entry_hash: string;
};

export type HardenEvent =
  | { type: "status"; phase: string; message: string }
  | {
      type: "identity";
      family: string;
      attack_name: string;
      genome_id: string;
      brief: string;
      known_families: string[];
      known_genomes: number;
    }
  | {
      type: "incumbent";
      n_txns: number;
      n_fraud: number;
      train_rows: number;
      calib_rows: number;
      threshold: number;
      archive_recall: number;
      detail: string;
    }
  | {
      type: "escape";
      n_fraud: number;
      escaped: number;
      caught: number;
      recall: number;
      escaped_value_minor: number;
      samples: { txn_id: string; amount_minor: number; score: number }[];
      detail: string;
    }
  | { type: "candidate"; train_rows: number; memory_rows: number; threshold: number; detail: string }
  | ({ type: "gauntlet" } & HardenGauntlet)
  | {
      type: "verdict";
      n_fraud: number;
      n_legit: number;
      before: HardenSide;
      after: HardenSide;
      newly_caught: number;
      value_recovered_minor: number;
      txns: HardenTxn[];
    }
  | {
      type: "ledger";
      entry_hash: string;
      prev_hash: string;
      generation: number;
      chain_length: number;
    }
  | { type: "done"; result: HardenResult }
  | { type: "error"; detail: string };

export async function streamHarden(
  text: string,
  onEvent: (ev: HardenEvent) => void,
  signal?: AbortSignal,
): Promise<HardenResult> {
  const res = await fetch(`${API_BASE}/api/harden/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (res.status === 404) {
    throw new Error(
      "The harden endpoint is missing. Restart the API to pick up the new routes: python -m hydraloop api",
    );
  }
  if (!res.ok || !res.body) {
    const err = await res.text();
    throw new Error(err.slice(0, 200) || `harden failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let result: HardenResult | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const ev = JSON.parse(line) as HardenEvent;
      onEvent(ev);
      if (ev.type === "error") throw new Error(ev.detail);
      if (ev.type === "done") result = ev.result;
    }
  }
  if (!result) throw new Error("harden stream ended without a verdict");
  return result;
}
