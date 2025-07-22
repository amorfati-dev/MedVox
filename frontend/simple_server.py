#!/usr/bin/env python3
"""
Super simple HTTP server for testing MedVox frontend
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to frontend directory
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)
    
    print(f"🦷 Simple MedVox Server")
    print(f"📁 Directory: {frontend_dir}")
    print(f"🔌 Port: {PORT}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print(f"🛑 Press Ctrl+C to stop\n")
    
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n🛑 Server stopped")

if __name__ == "__main__":
    main() 