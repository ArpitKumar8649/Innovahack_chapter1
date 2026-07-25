/* The court's roster — every agent that speaks in the transcript. */

export type AgentId =
  | "murli" | "researcher" | "extractor"
  | "verifier-a" | "verifier-b" | "verifier-c"
  | "judge" | "auditor" | "editor" | "writer" | "memory";

export interface Agent {
  id: AgentId;
  name: string;
  role: string;
  lens: string;
  sigil: string;      // short glyph for the avatar
  color: string;      // accent (css var name or hex)
}

export const AGENTS: Record<AgentId, Agent> = {
  murli: {
    id: "murli", name: "Murli", role: "Cognitive Scientist",
    lens: "Frames competing hypotheses, then attacks its own findings before the court convenes.",
    sigil: "M", color: "var(--gold)",
  },
  researcher: {
    id: "researcher", name: "Evidence", role: "Researcher",
    lens: "Requisitions full-text sources (Serper web/scholar/news → Tavily extract), hashed and indexed.",
    sigil: "E", color: "var(--accent)",
  },
  extractor: {
    id: "extractor", name: "Extractor", role: "Claim Analyst",
    lens: "Decomposes the corpus into atomic, evidence-anchored claims.",
    sigil: "X", color: "var(--accent-2)",
  },
  "verifier-a": {
    id: "verifier-a", name: "Verifier A", role: "Evidentialist",
    lens: "Literal evidence only — supports a claim only if a source states it verbatim.",
    sigil: "A", color: "var(--green)",
  },
  "verifier-b": {
    id: "verifier-b", name: "Verifier B", role: "Skeptic",
    lens: "Adversarial scrutiny — hunts outdated info, confused entities, unsourced numbers.",
    sigil: "B", color: "var(--red)",
  },
  "verifier-c": {
    id: "verifier-c", name: "Verifier C", role: "Contextualist",
    lens: "Precision & currency — checks dates, scope, and over-absolute statements.",
    sigil: "C", color: "var(--amber)",
  },
  judge: {
    id: "judge", name: "The Judge", role: "Arbiter",
    lens: "Rules when the panel cannot reach consensus — and records the dissent.",
    sigil: "§", color: "var(--gold)",
  },
  auditor: {
    id: "auditor", name: "Auditor", role: "Hallucination Detector",
    lens: "Typed sweep for entity, number, date, staleness and extrapolation failures.",
    sigil: "◍", color: "var(--amber)",
  },
  editor: {
    id: "editor", name: "Editor", role: "Contradiction Detector",
    lens: "Hostile reader — flags verifier splits, source refutations, internal conflicts.",
    sigil: "!", color: "var(--red)",
  },
  writer: {
    id: "writer", name: "Synthesis", role: "Writer",
    lens: "Compiles the citation-backed briefing from verified material only.",
    sigil: "✎", color: "var(--accent)",
  },
  memory: {
    id: "memory", name: "Memory", role: "Cross-run Recall",
    lens: "Surfaces prior findings and reuses freshly-verified claims.",
    sigil: "◈", color: "var(--accent-2)",
  },
};

/** Map a verdict's verifier tag ("A"|"B"|"C"|"J"|"M") to an agent id. */
export function agentForVerifier(tag: string): AgentId {
  switch (tag) {
    case "A": return "verifier-a";
    case "B": return "verifier-b";
    case "C": return "verifier-c";
    case "J": return "judge";
    case "M": return "memory";
    default: return "writer";
  }
}
