/* API base URL.
   - Local dev / single-container Docker: empty string (same-origin, nginx
     or serve_frontend.py proxies /api/* to the backend).
   - Split deploy (Vercel frontend + Render backend): set VITE_API_BASE to
     the Render URL, e.g. https://veritasai.onrender.com */
export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";
