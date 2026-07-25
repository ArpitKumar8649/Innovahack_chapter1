import { Reveal } from "../ui/Reveal";

const LAYERS = [
  {
    no: "01", title: "Content hash",
    body: "Every evidence chunk is SHA-256 hashed at extraction. A verdict that quotes a span is tied to that exact text.",
    tag: "SHA-256",
  },
  {
    no: "02", title: "Merkle anchoring",
    body: "A run's chunks form a Merkle tree; the report carries the root and a proof path per claim. Tamper with one quote and the root breaks.",
    tag: "Merkle root + proofs",
  },
  {
    no: "03", title: "Signed verdicts",
    body: "Each agent's verdict is HMAC-signed over verifier · claim · stance · quote. Agents can't be silently re-quoted after the fact.",
    tag: "HMAC / non-repudiation",
  },
  {
    no: "04", title: "Public verification",
    body: "GET /api/reports/{id}/verify recomputes the root and re-checks every signature. The UI also verifies in-browser — no trust in our server.",
    tag: "Web Crypto",
  },
];

export function ReceiptStack() {
  return (
    <section className="receipts wrap" id="receipts">
      <Reveal>
        <span className="eyebrow">fact-embedded citations</span>
        <h2 className="display section-title">Every claim shows its receipt.<br />And the receipt is math.</h2>
        <p className="section-sub">
          No more <em>“I read it on the internet.”</em> Citations here are
          tamper-evident cryptographic artifacts — four layers deep.
        </p>
      </Reveal>
      <div className="receipt-stack">
        {LAYERS.map((l, i) => (
          <Reveal key={l.no} delay={i * 90}>
            <div className="receipt">
              <div className="receipt-no mono">{l.no}</div>
              <div className="receipt-body">
                <div className="receipt-title">{l.title}</div>
                <p>{l.body}</p>
              </div>
              <span className="receipt-tag mono">{l.tag}</span>
              <span className="receipt-perf" aria-hidden />
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
