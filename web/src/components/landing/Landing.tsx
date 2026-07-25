import { Link } from "react-router-dom";
import { CourtOpening } from "./CourtOpening";
import { AgentRoster } from "./AgentRoster";
import { ReceiptStack } from "./ReceiptStack";
import { LiveNumbers } from "./LiveNumbers";
import { HowItWorks } from "./HowItWorks";
import { Reveal } from "../ui/Reveal";

export function Landing() {
  return (
    <main className="landing">
      <CourtOpening />
      <AgentRoster />
      <ReceiptStack />
      <LiveNumbers />
      <HowItWorks />

      <section className="cta wrap">
        <Reveal>
          <div className="cta-card">
            <h2 className="display">The court is in session.</h2>
            <p>Bring a claim. Watch it get argued, verified, and anchored.</p>
            <Link to="/court" className="btn btn-gold">Enter the court →</Link>
          </div>
        </Reveal>
      </section>

      <footer className="site-foot">
        <div className="wrap foot-inner">
          <span className="display foot-brand">⚖ VeritasAI</span>
          <span className="mono foot-note">
            autonomous multi-agent fact-verification · FEC: SHA-256 + Merkle + signed verdicts
          </span>
        </div>
      </footer>
    </main>
  );
}
