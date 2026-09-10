#!/usr/bin/env python3
"""Simple HTTP server for the Signalpost frontend with proper CORS and large file support."""
import http.server
import os
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from norway_company_agent.research import answer_profile, screen_profiles
except Exception:
    answer_profile = None
    screen_profiles = None

class SignalpostHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        if self.path.endswith(".json"):
            self.send_header("Content-Type", "application/json; charset=utf-8")
        super().end_headers()

    def do_POST(self):
        try:
            if self.path == '/api/chat':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                org_number = data.get('organisation_number')
                question = data.get('question')
                
                with open(os.path.join(DIRECTORY, 'data.json'), 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                
                company = next((c for c in companies if str(c.get('organisation_number')) == str(org_number) or str(c.get('profile', {}).get('organisation_number')) == str(org_number)), None)
                
                if company and answer_profile:
                    answer = answer_profile(company, question)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps(answer).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Company not found"}).encode('utf-8'))
                    
            elif self.path == '/api/screen':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                query = data.get('query')
                
                with open(os.path.join(DIRECTORY, 'data.json'), 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                    
                if screen_profiles:
                    results = screen_profiles(companies, query)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps(results).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            print(f"[Signalpost Error] {e}")

    def log_message(self, fmt, *args):
        print(f"[Signalpost] {args[0]}")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), SignalpostHandler) as httpd:
        print(f"Signalpost frontend serving on http://localhost:{PORT}")
        print(f"Serving files from: {DIRECTORY}")
        httpd.serve_forever()
