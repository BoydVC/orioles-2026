#!/usr/bin/env python3
"""Orioles 2026 Camden Yards night wall — stdlib server on 127.0.0.1:4278.
Serves dist/ (built snapshot + index) and /api/season + /api/research."""
import http.server, json, os, socketserver, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "4278"))
DIST = os.path.join(HERE, "dist")


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIST, **k)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/season":
            return self._json_file(os.path.join(HERE, "data", "season.json"))
        if path == "/api/research":
            p = os.path.join(HERE, "data", "research_notes.json")
            if os.path.exists(p):
                return self._json_file(p)
            return self._send(200, json.dumps({"label": "research unavailable", "sections": [], "gaps": []}).encode(), "application/json")
        if path in ("/healthz", "/api/health"):
            return self._send(200, b'{"ok":true,"app":"orioles-2026","port":4278}', "application/json")
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json_file(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
            json.loads(body)
            self._send(200, body, "application/json")
        except Exception as e:
            self._send(503, json.dumps({"error": str(e)}).encode(), "application/json")

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with S(("127.0.0.1", PORT), H) as srv:
        print(f"Orioles 2026 on http://127.0.0.1:{PORT}", flush=True)
        srv.serve_forever()
