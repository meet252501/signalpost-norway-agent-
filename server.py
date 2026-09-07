#!/usr/bin/env python3
import json
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add src to sys.path so we can import norway_company_agent
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.research import answer_profile, screen_profiles

class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "frontend"), **kwargs)
        
    def do_POST(self):
        try:
            if self.path == '/api/chat':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                org_number = data.get('organisation_number')
                question = data.get('question')
                
                # Load the companies from data.json
                with open(ROOT / 'frontend' / 'data.json', 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                
                # Find the company
                company = next((c for c in companies if str(c.get('organisation_number')) == str(org_number)), None)
                
                if company:
                    answer = answer_profile(company, question)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(answer).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Company not found"}).encode('utf-8'))
                    
            elif self.path == '/api/screen':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                query = data.get('query')
                
                # Load the companies from data.json
                with open(ROOT / 'frontend' / 'data.json', 'r', encoding='utf-8') as f:
                    companies = json.load(f)
                    
                results = screen_profiles(companies, query)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            print(f"Error handling POST: {e}")

def run(server_class=HTTPServer, handler_class=APIHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting API backend on http://localhost:{port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
