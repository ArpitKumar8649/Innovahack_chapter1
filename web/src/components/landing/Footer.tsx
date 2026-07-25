import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="footer-glow">
      {/* Rose glow effects */}
      <div className="footer-glow-effects">
        <div className="glow-orb glow-orb-1"></div>
        <div className="glow-orb glow-orb-2"></div>
      </div>

      {/* Glass container */}
      <div className="footer-glass wrap">
        <div className="footer-content">
          {/* Brand section */}
          <div className="footer-brand">
            <Link to="/" className="footer-logo">
              <span className="footer-logo-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
                  />
                </svg>
              </span>
              <span className="footer-logo-text">VeritasAI</span>
            </Link>
            <p className="footer-description">
              Autonomous multi-agent fact-verification system. Every claim is
              researched, argued, verified, and cryptographically anchored.
            </p>
            <div className="footer-social">
              <a href="https://github.com/veritasai" aria-label="GitHub" className="social-link">
                <svg className="social-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 .29a12 12 0 00-3.797 23.401c.6.11.82-.26.82-.577v-2.17c-3.338.726-4.042-1.415-4.042-1.415-.546-1.387-1.332-1.756-1.332-1.756-1.09-.744.084-.729.084-.729 1.205.085 1.84 1.237 1.84 1.237 1.07 1.835 2.809 1.306 3.495.999.106-.775.418-1.307.76-1.608-2.665-.301-5.466-1.332-5.466-5.933 0-1.31.469-2.381 1.236-3.222-.123-.303-.535-1.523.117-3.176 0 0 1.007-.322 3.301 1.23a11.502 11.502 0 016.002 0c2.292-1.552 3.297-1.23 3.297-1.23.654 1.653.242 2.873.119 3.176.77.841 1.235 1.912 1.235 3.222 0 4.61-2.805 5.629-5.476 5.925.429.369.813 1.096.813 2.211v3.285c0 .32.217.694.825.576A12 12 0 0012 .29"></path>
                </svg>
              </a>
              <a href="https://twitter.com/veritasai" aria-label="Twitter" className="social-link">
                <svg className="social-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19.633 7.997c.013.176.013.353.013.53 0 5.387-4.099 11.605-11.604 11.605A11.561 11.561 0 010 18.29c.373.044.734.074 1.12.074a8.189 8.189 0 005.065-1.737 4.102 4.102 0 01-3.834-2.85c.25.04.5.065.765.065.37 0 .734-.049 1.08-.147A4.092 4.092 0 01.8 8.582v-.05a4.119 4.119 0 001.853.522A4.099 4.099 0 01.812 5.847c0-.02 0-.042.002-.062a11.653 11.653 0 008.457 4.287A4.62 4.62 0 0122 5.924a8.215 8.215 0 002.018-.559 4.108 4.108 0 01-1.803 2.268 8.233 8.233 0 002.368-.648 8.897 8.897 0 01-2.062 2.112z" />
                </svg>
              </a>
              <a href="https://linkedin.com/company/veritasai" aria-label="LinkedIn" className="social-link">
                <svg className="social-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19 0h-14a5 5 0 00-5 5v14a5 5 0 005 5h14a5 5 0 005-5v-14a5 5 0 00-5-5zm-11 19h-3v-9h3zm-1.5-10.268a1.752 1.752 0 110-3.505 1.752 1.752 0 010 3.505zm15.5 10.268h-3v-4.5c0-1.07-.02-2.450-1.492-2.450-1.495 0-1.725 1.166-1.725 2.372v4.578h-3v-9h2.88v1.23h.04a3.157 3.157 0 012.847-1.568c3.042 0 3.605 2.003 3.605 4.612v4.726z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Navigation columns */}
          <nav className="footer-nav">
            <div className="footer-nav-col">
              <div className="footer-nav-title">Product</div>
              <ul className="footer-nav-list">
                <li><Link to="/court">The Court</Link></li>
                <li><a href="#agents">Agents</a></li>
                <li><a href="#receipts">FEC Receipts</a></li>
                <li><a href="#metrics">Live Metrics</a></li>
              </ul>
            </div>

            <div className="footer-nav-col">
              <div className="footer-nav-title">Technology</div>
              <ul className="footer-nav-list">
                <li><a href="#how-it-works">How It Works</a></li>
                <li><a href="#architecture">Architecture</a></li>
                <li><a href="#security">Security</a></li>
                <li><a href="#api">API</a></li>
              </ul>
            </div>

            <div className="footer-nav-col">
              <div className="footer-nav-title">Resources</div>
              <ul className="footer-nav-list">
                <li><a href="#docs">Documentation</a></li>
                <li><a href="#research">Research</a></li>
                <li><a href="#benchmarks">Benchmarks</a></li>
                <li><a href="#support">Support</a></li>
              </ul>
            </div>
          </nav>
        </div>

        {/* Bottom bar */}
        <div className="footer-bottom">
          <span>&copy; 2025 VeritasAI. All rights reserved.</span>
          <span className="footer-tech mono">
            FEC: SHA-256 + Merkle + Signed Verdicts
          </span>
        </div>
      </div>
    </footer>
  );
}
