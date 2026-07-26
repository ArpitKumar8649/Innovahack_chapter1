/* REST client for the VeritasAI API.
   Same-origin when API_BASE is empty (local/Docker); cross-origin when
   VITE_API_BASE points at the Render backend (Vercel split deploy). */
import type { Attestation, AuthUser, Calibration, Engagement, Health, MemoryStats, Report, RunSummary, SemanticStats } from "../types";
import { API_BASE } from "./config";

const TOKEN_KEY = "veritas_token";

/** Attach the Bearer token if one is stored. */
function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { ...extra, authorization: `Bearer ${token}` } : extra;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  // ---- auth ----
  register: async (email: string, name: string, password: string): Promise<{ token: string; user: AuthUser }> => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, name, password }),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Registration failed (HTTP ${res.status})`);
    }
    return res.json();
  },

  login: async (email: string, password: string): Promise<{ token: string; user: AuthUser }> => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Login failed (HTTP ${res.status})`);
    }
    return res.json();
  },

  me: async (): Promise<AuthUser> => {
    const d = await get<{ user: AuthUser }>("/api/auth/me");
    return d.user;
  },

  startResearch: async (topic: string, explain?: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/api/research`, {
      method: "POST",
      headers: authHeaders({ "content-type": "application/json" }),
      body: JSON.stringify({ topic, explain }),
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
  analytics: () => get<Engagement>("/api/analytics"),
  semantic: () => get<SemanticStats>("/api/semantic"),

  // Phase 8: observability & compliance
  getComplianceTrace: (runId: string) => get<any>(`/api/reports/${runId}/compliance`),
  replayWorkflow: (runId: string) => get<any>(`/api/workflows/${runId}/replay`),
  listWorkflows: (limit = 50) => get<any>(`/api/workflows?limit=${limit}`),

  // Phase 9: enterprise & adversarial maturity
  getRedTeamFindings: (runId: string) => get<any>(`/api/reports/${runId}/redteam`),
  createTenant: (name: string, plan = "free") =>
    fetch(`${API_BASE}/api/tenants?name=${encodeURIComponent(name)}&plan=${plan}`, { method: "POST" }).then(r => r.json()),
  listTenants: () => get<any>("/api/tenants"),
  getTenant: (tenantId: string) => get<any>(`/api/tenants/${tenantId}`),
  getTenantUsage: (tenantId: string, days = 30) => get<any>(`/api/tenants/${tenantId}/usage?days=${days}`),
  tenantStats: () => get<any>("/api/tenants/stats"),
  getPendingFeedback: (limit = 50) => get<any>(`/api/feedback/pending?limit=${limit}`),
  getPolicyRecommendations: () => get<any>("/api/feedback/policy"),
  getPolicyUpdates: (limit = 20) => get<any>(`/api/feedback/updates?limit=${limit}`),
  feedbackStats: () => get<any>("/api/feedback/stats"),

  recordEngagement: (payload: {
    run_id: string; topic: string; dwell_ms: number;
    inspector_opens: number; tree_views: number;
  }): void => {
    // fire-and-forget; engagement is best-effort telemetry
    fetch(`${API_BASE}/api/engagement`, {
      method: "POST",
      headers: authHeaders({ "content-type": "application/json" }),
      body: JSON.stringify(payload),
    }).catch(() => {});
  },
};
