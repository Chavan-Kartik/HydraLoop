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
