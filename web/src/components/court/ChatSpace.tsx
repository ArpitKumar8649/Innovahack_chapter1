import { useEffect, useRef } from "react";
import { AGENTS } from "../../lib/agents";
import type { RunState } from "../../hooks/useRun";
import { AgentMessage } from "./AgentMessage";
import { Avatar } from "../ui/Avatar";

/** The live transcript — every agent speaks as the run streams in. */
export function ChatSpace({ state }: { state: RunState }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [state.messages.length, state.activeAgent]);

  const active = state.activeAgent ? AGENTS[state.activeAgent] : null;

  return (
    <section className="chat-space">
      <div className="panel-head">
        <span className="panel-title display">The Floor</span>
        <span className="panel-sub mono">
          {state.status === "running" ? (
            <><span className="live-dot" /> in session</>
          ) : state.status === "done" ? (
            "verdict delivered"
          ) : (
            "awaiting a case"
          )}
        </span>
      </div>

      <div className="chat-scroll">
        {state.messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-sigil">⚖</div>
            <p>The court is quiet.</p>
            <p className="muted">Put a claim on trial and watch the agents argue it into receipts.</p>
          </div>
        )}

        {state.messages.map((m) => (
          <AgentMessage key={m.id} msg={m} />
        ))}

        {active && state.status === "running" && (
          <div className="agent-msg typing-row msg-enter">
            <Avatar agent={active} active />
            <div className="agent-msg-body">
              <div className="agent-msg-head">
                <span className="agent-name" style={{ color: active.color }}>{active.name}</span>
                <span className="agent-role">{active.role}</span>
              </div>
              <span className="typing" aria-label={`${active.name} is working`} />
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </section>
  );
}
