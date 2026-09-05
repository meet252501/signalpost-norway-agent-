#!/usr/bin/env python3
"""Simple HTTP server for the Signalpost frontend with proper CORS and large file support."""
import http.server
import os
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class SignalpostHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        if self.path.endswith(".json"):
            self.send_header("Content-Type", "application/json; charset=utf-8")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"[Signalpost] {args[0]}")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), SignalpostHandler) as httpd:
        print(f"Signalpost frontend serving on http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        httpd.serve_forever()
