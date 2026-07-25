import type { Agent } from "../../lib/agents";

export function Avatar({ agent, size = 38, active = false }: {
  agent: Agent; size?: number; active?: boolean;
}) {
  return (
    <div
      className={active ? "avatar active" : "avatar"}
      style={{
        width: size, height: size,
        color: agent.color,
        borderColor: agent.color,
        background: `color-mix(in srgb, ${agent.color} 12%, transparent)`,
        fontSize: size * 0.42,
      }}
      title={`${agent.name} — ${agent.role}`}
    >
      {agent.sigil}
    </div>
  );
}
