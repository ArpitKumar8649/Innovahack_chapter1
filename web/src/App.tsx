import { Link, Route, Routes, useLocation } from "react-router-dom";
import { Landing } from "./components/landing/Landing";
import { CourtView } from "./components/court/CourtView";
import { SignIn } from "./components/auth/SignIn";
import { SignUp } from "./components/auth/SignUp";
import { Pricing } from "./components/pricing/Pricing";

function TopBar() {
  const { pathname } = useLocation();
  // Full-screen pages (auth, pricing) render their own chrome — no topbar.
  const bare = pathname === "/signin" || pathname === "/signup" || pathname === "/pricing";
  if (bare) return null;
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        <span className="brand-sigil">⚖</span>
        <span className="brand-name display">VeritasAI</span>
        <span className="brand-tag mono">the research court</span>
      </Link>
      <nav className="topnav">
        <Link to="/" className={pathname === "/" ? "nav-link active" : "nav-link"}>Overview</Link>
        <Link to="/court" className={pathname.startsWith("/court") ? "nav-link active" : "nav-link"}>
          Enter the Court
        </Link>
        <Link to="/pricing" className={pathname === "/pricing" ? "nav-link active" : "nav-link"}>
          Pricing
        </Link>
        <Link to="/signin" className="nav-auth btn-rose">Sign in</Link>
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <>
      <TopBar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/court" element={<CourtView />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/pricing" element={<Pricing />} />
      </Routes>
    </>
  );
}
