import { Link } from "react-router-dom";
import { CourtOpening } from "./CourtOpening";
import { AgentRoster } from "./AgentRoster";
import { ReceiptStack } from "./ReceiptStack";
import { LiveNumbers } from "./LiveNumbers";
import { HowItWorks } from "./HowItWorks";
import { Footer } from "./Footer";
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
            <Link to="/court" className="btn btn-rose">Enter the court →</Link>
          </div>
        </Reveal>
      </section>

      <Footer />
    </main>
  );
}
