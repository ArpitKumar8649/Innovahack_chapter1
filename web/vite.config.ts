import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI backend is API-only on :8000. In dev, Vite proxies /api there
// (mirroring the production nginx edge in deploy/nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // SSE must not be buffered
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
              proxyRes.headers["cache-control"] = "no-cache";
              proxyRes.headers["x-accel-buffering"] = "no";
            }
          });
        },
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
