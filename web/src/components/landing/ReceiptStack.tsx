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

/* the pin from the reference design */
const Pin = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path stroke="none" d="M0 0h24v24H0z" fill="none" />
    <path d="M16 3a1 1 0 0 1 .117 1.993l-.117 .007v4.764l1.894 3.789a1 1 0 0 1 .1 .331l.006 .116v2a1 1 0 0 1 -.883 .993l-.117 .007h-4v4a1 1 0 0 1 -1.993 .117l-.007 -.117v-4h-4a1 1 0 0 1 -.993 -.883l-.007 -.117v-2a1 1 0 0 1 .06 -.34l.046 -.107l1.894 -3.791v-4.762a1 1 0 0 1 -.117 -1.993l.117 -.007h8z" />
  </svg>
);

/* animated dashed path weaving between the pinned notes (desktop only) */
const CONNECTOR_D =
  "M 290 150 C 500 150, 550 270, 710 270 C 850 270, 500 350, 290 450 C 290 600, 550 720, 750 720";

export function ReceiptStack() {
  return (
    <section className="receipts" id="receipts">
      <div className="wrap">
        <Reveal>
          <span className="eyebrow">fact-embedded citations</span>
          <h2 className="display section-title">
            Every claim shows its receipt.<br />And the receipt is math.
          </h2>
          <p className="section-sub">
            No more <em>“I read it on the internet.”</em> Citations here are
            tamper-evident cryptographic artifacts — four layers deep.
          </p>
        </Reveal>
      </div>

      {/* the pin-board */}
      <div className="receipts-board-wrap wrap">
       <div className="receipts-board">
          {/* dashed connector, animated */}
          <svg className="receipts-path" viewBox="0 0 1000 900" preserveAspectRatio="none" aria-hidden>
            <path d={CONNECTOR_D} fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          </svg>

          {LAYERS.map((l, i) => (
            <Reveal key={l.no} delay={i * 110} className={`receipt-note pos-${i + 1}`}>
              <div className={`note-outer theme-${i + 1} glow-card`}>
                <Pin className="note-pin" />
                <div className="note-inner">
                  <span className="note-number">{l.no}</span>
                  <h3 className="note-title">{l.title}</h3>
                  <p className="note-desc">{l.body}</p>
                  <span className="note-tag mono">{l.tag}</span>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
