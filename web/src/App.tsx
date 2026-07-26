import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Landing } from "./components/landing/Landing";
import { CourtView } from "./components/court/CourtView";
import { SignIn } from "./components/auth/SignIn";
import { SignUp } from "./components/auth/SignUp";
import { Pricing } from "./components/pricing/Pricing";
import { useAuth } from "./auth";

function TopBar() {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  // Full-screen pages (auth, pricing) render their own chrome — no topbar.
  const bare = pathname === "/signin" || pathname === "/signup" || pathname === "/pricing";
  if (bare) return null;

  const close = () => setMenuOpen(false);

  return (
    <header className="topbar">
      <Link to="/" className="brand" onClick={close}>
        <span className="brand-sigil">⚖</span>
        <span className="brand-name display">VeritasAI</span>
        <span className="brand-tag mono">the research court</span>
      </Link>

      {/* hamburger (mobile only) */}
      <button
        className={`nav-burger ${menuOpen ? "open" : ""}`}
        onClick={() => setMenuOpen((o) => !o)}
        aria-label="Toggle menu"
        aria-expanded={menuOpen}
      >
        <span /><span /><span />
      </button>

      <nav className={`topnav ${menuOpen ? "open" : ""}`}>
        <Link to="/" onClick={close} className={pathname === "/" ? "nav-link active" : "nav-link"}>Overview</Link>
        <Link to="/court" onClick={close} className={pathname.startsWith("/court") ? "nav-link active" : "nav-link"}>
          Enter the Court
        </Link>
        <Link to="/pricing" onClick={close} className={pathname === "/pricing" ? "nav-link active" : "nav-link"}>
          Pricing
        </Link>
        {user ? (
          <div className="nav-user">
            <span className="nav-user-name mono" title={user.email}>{user.name}</span>
            <button className="nav-auth btn-rose" onClick={() => { logout(); close(); }}>Sign out</button>
          </div>
        ) : (
          <Link to="/signin" onClick={close} className="nav-auth btn-rose">Sign in</Link>
        )}
      </nav>
    </header>
  );
}

/** Gate: redirect to /signin unless authenticated. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="auth-loading">Verifying session…</div>;
  if (!user) return <Navigate to="/signin" replace state={{ from: location }} />;
  return <>{children}</>;
}

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/court" element={<RequireAuth><CourtView /></RequireAuth>} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/pricing" element={<Pricing />} />
      </Routes>
    </>
  );
}
