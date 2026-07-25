import { useEffect, useMemo, useState } from "react";
import type { Claim, Report } from "../../types";
import { sha256Hex, verifyMerkle } from "../../lib/merkle";
import { TIER_LABEL } from "./tiers";

function highlightQuote(chunkText: string, quote: string): { before: string; match: string; after: string } | null {
  if (!quote) return null;
  const idx = chunkText.toLowerCase().indexOf(quote.toLowerCase());
  if (idx === -1) return null;
  return {
    before: chunkText.slice(0, idx),
    match: chunkText.slice(idx, idx + quote.length),
    after: chunkText.slice(idx + quote.length, idx + quote.length + 600),
  };
}

/** FEC receipt panel: exact quote in its chunk, hash, and a Merkle proof
    verified in the browser (no server trust). */
export function EvidenceInspector({ claim, report, focusChunk, onClose }: {
  claim: Claim;
  report: Report;
  focusChunk?: string;
  onClose: () => void;
}) {
  const { chunkMap, srcByChunk } = useMemo(() => {
    const cm = new Map<string, { chunk_id: string; text: string; hash: string }>();
    const sm = new Map<string, Report["sources"][number]>();
    for (const s of report.sources) {
      for (const ch of s.chunks) { cm.set(ch.chunk_id, ch); sm.set(ch.chunk_id, s); }
    }
    return { chunkMap: cm, srcByChunk: sm };
  }, [report]);

  const order = useMemo(() => {
    const ids = focusChunk
      ? [focusChunk, ...claim.chunk_ids.filter((x) => x !== focusChunk)]
      : claim.chunk_ids;
    return ids.filter((id) => chunkMap.has(id));
  }, [claim, focusChunk, chunkMap]);

  // per-chunk proof status: "checking" | "ok" | "bad"
  const [proofs, setProofs] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next: Record<string, string> = {};
      for (const cid of order) {
        const ch = chunkMap.get(cid)!;
        const proof = claim.merkle_proofs?.[cid];
        try {
          const leaf = await sha256Hex(ch.text);
          const hashOk = leaf === ch.hash;
          const proofOk = await verifyMerkle(ch.hash, proof, report.merkle_root);
          next[cid] = hashOk && proofOk ? "ok" : "bad";
        } catch {
          next[cid] = "bad";
        }
        if (!cancelled) setProofs({ ...next });
      }
    })();
    return () => { cancelled = true; };
  }, [order, chunkMap, claim, report.merkle_root]);

  const quote = claim.verdicts.find((v) => v.chunk_id && v.quote)?.quote ?? "";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h4 className="display">▣ Evidence Inspector</h4>
          <button className="modal-close" onClick={onClose} aria-label="close">✕</button>
        </div>
        <div className="modal-body">
          <div className="insp-claim">{claim.text}</div>
          <span className={`status-pill status-${claim.status}`}>{claim.status} · {claim.confidence}%</span>

          <h5 className="insp-h">Anchored evidence — verified in your browser, no server trust</h5>
          {order.map((cid) => {
            const ch = chunkMap.get(cid)!;
            const s = srcByChunk.get(cid)!;
            const hl = highlightQuote(ch.text, quote);
            const status = proofs[cid] ?? "checking";
            return (
              <div key={cid} className="insp-chunk">
                <div className="insp-chunk-head">
                  <b className="mono">{cid}</b>
                  <span className={`tier tier-${s.authority_tier}`}>
                    T{s.authority_tier} · {s.authority_label || TIER_LABEL[s.authority_tier] || ""}
                  </span>
                  <a href={s.url} target="_blank" rel="noopener noreferrer">{s.publisher}</a>
                  <span className={`insp-proof ${status}`}>
                    {status === "checking" ? "… verifying Merkle proof" : status === "ok" ? "✓ Merkle-verified in browser" : "✗ verification failed"}
                  </span>
                </div>
                <div className="insp-text">
                  {hl ? (
                    <>{hl.before}<mark>{hl.match}</mark>{hl.after}</>
                  ) : (
                    ch.text.slice(0, 900)
                  )}
                </div>
                <div className="insp-hash mono">SHA-256: {ch.hash.slice(0, 24)}…</div>
              </div>
            );
          })}

          <h5 className="insp-h">Verifier verdicts (HMAC-signed)</h5>
          <div className="insp-verdicts">
            {claim.verdicts.map((v, i) => (
              <div key={i} className={`insp-v v-${v.stance}`}>
                <b>{v.verifier} — {v.stance}</b>
                {v.quote && !v.span_valid && <span className="v-void-tag">quote voided</span>}
                <p>{v.reasoning}</p>
                {v.quote && <blockquote>“{v.quote.slice(0, 280)}”</blockquote>}
                <code className="insp-sig">sig {v.signature}</code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
