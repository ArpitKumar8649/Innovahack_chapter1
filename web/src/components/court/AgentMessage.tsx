import { AGENTS } from "../../lib/agents";
import type { ChatMessage } from "../../hooks/useRun";
import { Avatar } from "../ui/Avatar";
import { StanceChip } from "../ui/StanceChip";

const ACTION_LABEL: Record<string, string> = {
  concede: "concedes", rebut: "rebuts", hold: "holds", judge: "rules", cache: "from memory",
};

/** One agent's turn in the transcript. */
export function AgentMessage({ msg }: { msg: ChatMessage }) {
  const agent = AGENTS[msg.agent];
  const isSystem = msg.kind === "system";
  const action = msg.action && ACTION_LABEL[msg.action] ? ACTION_LABEL[msg.action] : null;

  return (
    <div className={`agent-msg msg-enter kind-${msg.kind}`} style={{ ["--agent-color" as string]: agent.color }}>
      <Avatar agent={agent} />
      <div className="agent-msg-body">
        <div className="agent-msg-head">
          <span className="agent-name" style={{ color: agent.color }}>{agent.name}</span>
          <span className="agent-role">{agent.role}</span>
          {msg.round !== undefined && msg.round > 1 && (
            <span className="round-tag mono">R{msg.round}</span>
          )}
          {action && <span className={`action-tag act-${msg.action}`}>{action}</span>}
          {msg.stance && <StanceChip stance={msg.stance} spanValid={msg.spanValid} />}
        </div>

        {msg.kind === "hypothesis" || msg.kind === "claims" ? (
          <pre className="agent-msg-list">{msg.text}</pre>
        ) : (
          <p className="agent-msg-text">{msg.text}</p>
        )}

        {msg.quote && (
          <blockquote className={`agent-quote ${msg.spanValid === false ? "void" : ""}`}>
            “{msg.quote}”
            {msg.chunkId && <span className="quote-chunk mono">{msg.chunkId}</span>}
            {msg.spanValid === false && <span className="quote-void">span not in corpus — voided</span>}
          </blockquote>
        )}

        {msg.dissent && (
          <div className="agent-dissent">
            <span className="dissent-label">dissent on record</span>
            {msg.dissent}
          </div>
        )}
      </div>
      {!isSystem && <span className="msg-rail" style={{ background: agent.color }} />}
    </div>
  );
}
