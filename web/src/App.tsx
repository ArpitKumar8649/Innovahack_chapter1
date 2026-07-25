import { Link, Route, Routes, useLocation } from "react-router-dom";
import { Landing } from "./components/landing/Landing";
import { CourtView } from "./components/court/CourtView";

function TopBar() {
  const { pathname } = useLocation();
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
      </Routes>
    </>
  );
}
