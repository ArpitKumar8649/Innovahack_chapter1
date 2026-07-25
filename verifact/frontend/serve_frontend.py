#!/usr/bin/env python3
"""Development server for the VeritasAI frontend.

Serves the static frontend on :3000 and proxies /api/* to the backend on
:8000 — mirroring the production nginx edge (deploy/nginx.conf) exactly,
including SSE streaming. The app is used from a single URL in development:
http://localhost:3000
"""
import http.server
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_BASE = "http://localhost:8000"
PORT = 3000
HOP_BY_HOP = {"transfer-encoding", "content-length", "connection", "keep-alive"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(404)

    def _proxy(self, method):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(API_BASE + self.path, data=body, method=method)
        if self.headers.get("content-type"):
            req.add_header("content-type", self.headers["content-type"])
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            resp = e  # HTTPError is a response too
        except Exception as e:
            self.send_error(502, f"backend unreachable: {e}")
            return
        try:
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.end_headers()
            # stream the body chunk-by-chunk so SSE events arrive live
            # (read1 = return whatever is available, never wait for a full buffer)
            read = getattr(resp, "read1", resp.read)
            while True:
                chunk = read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client disconnected mid-stream
        finally:
            resp.close()

    def log_message(self, fmt, *args):
        pass  # keep the dev console quiet


if __name__ == "__main__":
    print(f"VeritasAI frontend → http://localhost:{PORT}  (API proxied to {API_BASE})")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
