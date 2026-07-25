/* REST client for the VeritasAI API (same-origin; proxied to :8000). */
import type { Attestation, Calibration, Health, MemoryStats, Report, RunSummary } from "../types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  startResearch: async (topic: string): Promise<string> => {
    const res = await fetch("/api/research", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    if (!res.ok) throw new Error(`could not start run (HTTP ${res.status})`);
    const d = await res.json();
    return d.run_id as string;
  },

  getRun: (runId: string) =>
    get<{ run_id: string; topic: string; done: boolean; error: string | null; report: Report | null }>(
      `/api/research/${runId}`,
    ),

  verify: (runId: string) => get<Attestation>(`/api/reports/${runId}/verify`),

  listRuns: async (): Promise<RunSummary[]> => {
    const d = await get<{ runs: RunSummary[] }>("/api/runs");
    return d.runs;
  },

  memory: () => get<MemoryStats>("/api/memory"),
  calibration: () => get<Calibration>("/api/calibration"),
  health: () => get<Health>("/api/health"),
};
