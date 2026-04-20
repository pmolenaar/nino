#!/usr/bin/env python3
"""
El Niño Monitor — HTTP API voor Home Assistant.

Serveert state.json op /api/state zodat HA het kan uitlezen
via de REST sensor integratie.

Gebruik: python nino_server.py [--port 8099]
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import argparse

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "data" / "state.json"
DEFAULT_PORT = 8099


class NinoHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/api/state":
            self._serve_state()
        elif self.path == "/api/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def _serve_state(self):
        if not STATE_FILE.exists():
            self._respond(503, {"error": "no data yet, run nino_monitor.py first"})
            return
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            self._respond(200, state)
        except (json.JSONDecodeError, OSError) as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Stille logging — alleen errors
        if args and "200" not in str(args[0]):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="El Niño Monitor API")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--bind", default="0.0.0.0")
    args = parser.parse_args()

    server = HTTPServer((args.bind, args.port), NinoHandler)
    print(f"El Niño API draait op http://{args.bind}:{args.port}")
    print(f"  GET /api/state  — huidige ENSO status")
    print(f"  GET /api/health — health check")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGestopt.")
        server.server_close()


if __name__ == "__main__":
    main()
