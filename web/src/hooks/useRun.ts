/* useRun — folds the SSE event stream into UI state.
   Chat messages and terminal lines are both derived from the same events,
   so the chat space and the terminal stay perfectly in sync with the backend. */
import { useCallback, useEffect, useReducer, useRef } from "react";
import type {
  Attestation, Claim, Hypothesis, Prior, Report, Source, StageName, Stance,
} from "../types";
import { streamRun } from "../lib/sse";
import { agentForVerifier, type AgentId } from "../lib/agents";
import { api } from "../lib/api";

let _seq = 0;
const uid = (p: string) => `${p}-${_seq++}`;

export type MsgKind =
  | "hypothesis" | "evidence" | "claims" | "verdict" | "deliberation"
  | "judgment" | "memory" | "hallucination" | "contradiction" | "synthesis" | "system";

export interface ChatMessage {
  id: string;
  agent: AgentId;
  kind: MsgKind;
  text: string;
  quote?: string;
  chunkId?: string;
  stance?: Stance;
  spanValid?: boolean;
  action?: string;
  round?: number;
  dissent?: string;
  claimId?: number;
  ts: number;
}

export interface LogLine {
  id: string;
  ts: number;
  level: "info" | "stage" | "warn" | "error";
  stage: string;
  text: string;
}

export interface RunState {
  status: "idle" | "running" | "done" | "error";
  runId: string | null;
  topic: string;
  stage: StageName | null;
  stagesDone: Partial<Record<StageName, boolean>>;
  activeAgent: AgentId | null;
  logs: LogLine[];
  messages: ChatMessage[];
  claims: Claim[];
  sources: Source[];
  hypotheses: Hypothesis[];
  priors: Prior[];
  report: Report | null;
  attestation: Attestation | null;
  error: string | null;
  elapsed: number | null;
}

const initial: RunState = {
  status: "idle", runId: null, topic: "", stage: null, stagesDone: {},
  activeAgent: null, logs: [], messages: [], claims: [], sources: [],
  hypotheses: [], priors: [], report: null, attestation: null,
  error: null, elapsed: null,
};

const STAGE_AGENT: Partial<Record<StageName, AgentId>> = {
  intake: "memory", hypothesize: "murli", research: "researcher",
  extract: "extractor", verify: "verifier-a", deliberate: "judge",
  hallucinations: "auditor", contradictions: "editor", report: "writer",
};

type Action =
  | { type: "reset"; topic: string; runId: string }
  | { type: "stage"; stage: StageName; status: "started" | "done" }
  | { type: "log"; stage: string; message: string }
  | { type: "priors"; priors: Prior[] }
  | { type: "hypotheses"; hypotheses: Hypothesis[]; queries: string[] }
  | { type: "sources"; sources: Source[]; cached?: boolean }
  | { type: "claims"; claims: Claim[] }
  | { type: "cache"; cached: { claim_id: number; text: string; confidence: number; status: string }[] }
  | { type: "verdict"; claim_id: number; verifier: string; stance: Stance; reasoning: string; quote: string; chunk_id: string; span_valid: boolean }
  | { type: "debate"; transcript: Report["transcript"]; rounds: number }
  | { type: "hallucination"; claim_id: number; htype: string; severity: string; evidence: string }
  | { type: "contradiction"; claim_id: number; kind: string; description: string }
  | { type: "report"; report: Report }
  | { type: "done"; elapsed: number }
  | { type: "error"; message: string }
  | { type: "attestation"; attestation: Attestation };

function pushMsg(s: RunState, m: Omit<ChatMessage, "id" | "ts">): ChatMessage[] {
  return [...s.messages, { ...m, id: uid("m"), ts: Date.now() }];
}
function pushLog(s: RunState, level: LogLine["level"], stage: string, text: string): LogLine[] {
  return [...s.logs, { id: uid("l"), ts: Date.now(), level, stage, text }];
}

function reducer(s: RunState, a: Action): RunState {
  switch (a.type) {
    case "reset":
      return { ...initial, status: "running", runId: a.runId, topic: a.topic };

    case "stage": {
      const stagesDone = { ...s.stagesDone };
      if (a.status === "done") stagesDone[a.stage] = true;
      return {
        ...s, stage: a.stage, stagesDone,
        activeAgent: a.status === "started" ? STAGE_AGENT[a.stage] ?? null : s.activeAgent,
        logs: pushLog(s, "stage", a.stage, `▸ ${a.stage} ${a.status}`),
      };
    }

    case "log":
      return { ...s, logs: pushLog(s, "info", a.stage, a.message) };

    case "priors":
      return {
        ...s, priors: a.priors,
        messages: a.priors.length
          ? pushMsg(s, {
              agent: "memory", kind: "memory",
              text: `Recalled ${a.priors.length} prior finding${a.priors.length > 1 ? "s" : ""} related to this topic from past investigations.`,
            })
          : s.messages,
      };

    case "hypotheses":
      return {
        ...s, hypotheses: a.hypotheses,
        messages: pushMsg(s, {
          agent: "murli", kind: "hypothesis",
          text: a.hypotheses.map((h) => `${h.id} · ${h.statement}`).join("\n"),
        }),
      };

    case "sources": {
      const best = Math.min(...a.sources.map((x) => x.authority_tier));
      return {
        ...s, sources: a.sources,
        messages: pushMsg(s, {
          agent: "researcher", kind: "evidence",
          text: a.cached
            ? `Evidence cache hit — reusing ${a.sources.length} previously extracted sources (skipped search).`
            : `Extracted full text from ${a.sources.length} sources (best authority T${best}). Corpus chunked and content-hashed.`,
        }),
      };
    }

    case "claims":
      return {
        ...s, claims: a.claims,
        messages: pushMsg(s, {
          agent: "extractor", kind: "claims",
          text: `Decomposed into ${a.claims.length} atomic claims, each anchored to evidence chunks:\n` +
            a.claims.map((c) => `C${c.id} · ${c.text}`).join("\n"),
        }),
      };

    case "cache":
      return {
        ...s,
        messages: pushMsg(s, {
          agent: "memory", kind: "memory",
          text: `${a.cached.length} claim${a.cached.length > 1 ? "s" : ""} reused from memory (verified <24h ago) — skipping the panel: ` +
            a.cached.map((c) => `C${c.claim_id}`).join(", "),
        }),
      };

    case "verdict":
      return {
        ...s,
        messages: pushMsg(s, {
          agent: agentForVerifier(a.verifier), kind: "verdict",
          text: a.reasoning, quote: a.quote, chunkId: a.chunk_id,
          stance: a.stance, spanValid: a.span_valid, round: 1, claimId: a.claim_id,
        }),
      };

    case "debate": {
      const msgs = a.transcript.filter((e) => e.round > 1).map((e) => {
        const isJudge = e.verifier === "J";
        return {
          id: uid("m"), ts: Date.now(),
          agent: agentForVerifier(e.verifier),
          kind: (isJudge ? "judgment" : "deliberation") as MsgKind,
          text: e.reasoning, quote: e.quote, chunkId: e.chunk_id,
          stance: e.stance, spanValid: e.span_valid, action: e.action,
          round: e.round, dissent: e.dissent, claimId: e.claim_id,
        } satisfies ChatMessage;
      });
      return { ...s, messages: [...s.messages, ...msgs] };
    }

    case "hallucination":
      return {
        ...s,
        messages: pushMsg(s, {
          agent: "auditor", kind: "hallucination",
          text: `C${a.claim_id} — ${a.htype} (${a.severity}): ${a.evidence}`,
        }),
        logs: pushLog(s, "warn", "hallucinations", `flag C${a.claim_id} ${a.htype}`),
      };

    case "contradiction":
      return {
        ...s,
        messages: pushMsg(s, {
          agent: "editor", kind: "contradiction",
          text: `C${a.claim_id} — ${a.kind.replace(/_/g, " ")}: ${a.description}`,
        }),
        logs: pushLog(s, "warn", "contradictions", `C${a.claim_id} ${a.kind}`),
      };

    case "report":
      return {
        ...s, report: a.report, claims: a.report.claims,
        messages: pushMsg(s, {
          agent: "writer", kind: "synthesis", text: a.report.summary,
        }),
      };

    case "done":
      return { ...s, status: "done", activeAgent: null, elapsed: a.elapsed,
        logs: pushLog(s, "info", "done", `verdict delivered in ${a.elapsed}s`) };

    case "error":
      return { ...s, status: "error", activeAgent: null, error: a.message,
        logs: pushLog(s, "error", "error", a.message) };

    case "attestation":
      return { ...s, attestation: a.attestation };

    default:
      return s;
  }
}

export function useRun() {
  const [state, dispatch] = useReducer(reducer, initial);
  const closeRef = useRef<(() => void) | null>(null);

  const start = useCallback(async (topic: string, explain?: string) => {
    closeRef.current?.();
    const runId = await api.startResearch(topic, explain);
    dispatch({ type: "reset", topic, runId });

    closeRef.current = streamRun(runId, {
      stage: (d) => dispatch({ type: "stage", stage: d.stage, status: d.status }),
      log: (d) => dispatch({ type: "log", stage: d.stage, message: d.message }),
      priors: (d) => dispatch({ type: "priors", priors: d.priors }),
      hypotheses: (d) => dispatch({ type: "hypotheses", hypotheses: d.hypotheses, queries: d.queries }),
      sources: (d) => dispatch({ type: "sources", sources: d.sources, cached: d.cached }),
      claims: (d) => dispatch({ type: "claims", claims: d.claims }),
      cache: (d) => dispatch({ type: "cache", cached: d.cached }),
      verdict: (d) => dispatch({ type: "verdict", ...d }),
      debate: (d) => dispatch({ type: "debate", transcript: d.transcript, rounds: d.rounds }),
      hallucination: (d) => dispatch({ type: "hallucination", claim_id: d.claim_id, htype: d.type, severity: d.severity, evidence: d.evidence }),
      contradiction: (d) => dispatch({ type: "contradiction", claim_id: d.claim_id, kind: d.kind, description: d.description }),
      report: (d) => dispatch({ type: "report", report: d }),
      done: (d) => {
        dispatch({ type: "done", elapsed: d.elapsed_s });
        api.verify(runId).then((att) => dispatch({ type: "attestation", attestation: att })).catch(() => {});
      },
      error: (d) => dispatch({ type: "error", message: d.message }),
    });
  }, []);

  const loadReport = useCallback(async (runId: string) => {
    closeRef.current?.();
    const d = await api.getRun(runId);
    if (!d.report) return;
    dispatch({ type: "reset", topic: d.topic, runId });
    dispatch({ type: "report", report: d.report });
    dispatch({ type: "done", elapsed: 0 });
    api.verify(runId).then((att) => dispatch({ type: "attestation", attestation: att })).catch(() => {});
  }, []);

  useEffect(() => () => closeRef.current?.(), []);

  return { state, start, loadReport };
}
