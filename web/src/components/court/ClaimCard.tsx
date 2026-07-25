import type { Claim, Source } from "../../types";
import { StanceChip } from "../ui/StanceChip";

const ACTION_GLYPH: Record<string, string> = {
  concede: "↩", rebut: "⚔", hold: "≡", judge: "⚖", cache: "◈",
};

export function ClaimCard({ claim, sources, onInspect }: {
  claim: Claim;
  sources: Map<number, Source>;
  onInspect: (claimId: number, chunkId?: string) => void;
}) {
  const fromMemory = claim.verdicts.some((v) => v.verifier === "M");

  return (
    <article className={`claim-card status-edge-${claim.status} ${fromMemory ? "from-memory" : ""}`}>
      <div className="claim-head">
        <span className={`status-pill status-${claim.status}`}>{claim.status}</span>
        {fromMemory && <span className="mem-tag" title="reused from cross-run memory">◈ from memory</span>}
        <span className="claim-type mono">{claim.claim_type}{claim.hypothesis_id ? ` · ${claim.hypothesis_id}` : ""}</span>
        <div className="conf-bar" title={`confidence ${claim.confidence}%`}>
          <div className={`conf-fill status-${claim.status}`} style={{ width: `${claim.confidence}%` }} />
          <span className="conf-num mono">{claim.confidence}%</span>
        </div>
      </div>

      <p className="claim-text">
        {claim.text}{" "}
        {claim.source_ids.map((n) => {
          const s = sources.get(n);
          return s ? (
            <a key={n} className="cite" href={s.url} target="_blank" rel="noopener noreferrer">[{n}]</a>
          ) : null;
        })}
      </p>

      {claim.hallucinations.map((h, i) => (
        <div key={i} className={`hallu-flag hallu-${h.severity}`}>
          ◍ {h.type} — {h.evidence}
          {h.correction && <><br /><b>Correction:</b> {h.correction}</>}
        </div>
      ))}

      {claim.semantic_prior && (
        <div className="semantic-prior" title="semantically identical to a claim verified in a past run">
          ⟲ verified before — {Math.round(claim.semantic_prior.similarity * 100)}% match to a past-run claim
        </div>
      )}

      {claim.counter_evidence.length > 0 && (
        <div className="counter-evidence">
          <div className="counter-head">
            <span className="counter-flag">⟂ counter-evidence the search missed</span>
            <span className="counter-note mono">semantic retrieval · {claim.counter_evidence.length} opposing passage(s)</span>
          </div>
          {claim.counter_evidence.map((ce) => (
            <div key={ce.chunk_id} className="counter-item">
              <span className={`tier tier-${ce.authority_tier}`}>T{ce.authority_tier}</span>
              <span className="counter-text">{ce.text}</span>
              <span className="counter-meta mono">
                {ce.publisher && <em>{ce.publisher}</em>}
                <b>+{ce.score.toFixed(2)}</b>
                {ce.url && <a href={ce.url} target="_blank" rel="noopener noreferrer">↗</a>}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="claim-foot">
        <div className="claim-verdicts">
          {claim.verdicts.map((v, i) => (
            <span
              key={i}
              className={`vb st-${v.stance} ${v.quote && !v.span_valid ? "v-void" : ""}`}
              title={`${v.reasoning}\n${v.span_valid ? "quote verified in corpus" : "quote NOT found in corpus — verdict voided"}`}
            >
              {v.verifier} <StanceChip stance={v.stance} spanValid={v.span_valid} label="" />
              {v.round > 1 && <i className="mono"> R{v.round}{v.action ? ` ${ACTION_GLYPH[v.action] ?? ""}` : ""}</i>}
            </span>
          ))}
        </div>
        <div className="claim-evidence">
          {claim.chunk_ids.map((cid) => (
            <button key={cid} className="ev-chip mono" onClick={() => onInspect(claim.id, cid)}>
              ▣ {cid}
            </button>
          ))}
        </div>
      </div>

      {claim.verification_note && <div className="claim-note">{claim.verification_note}</div>}
    </article>
  );
}
