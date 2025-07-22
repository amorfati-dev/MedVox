#!/usr/bin/env python3
"""
Simple HTTPS server for testing MedVox frontend
Microphone access requires HTTPS in most browsers
"""

import http.server
import ssl
import os
import sys
from pathlib import Path

# Configuration
PORT = 3000
HOST = '0.0.0.0'  # Allow access from iPad on same network

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP handler with CORS headers"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def guess_type(self, path):
        """Override to handle missing file extensions"""
        result = super().guess_type(path)
        
        if path.endswith('.js'):
            return 'application/javascript'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.json'):
            return 'application/json'
        
        return result

def create_self_signed_cert():
    """Create a self-signed certificate for HTTPS"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Bavaria"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Munich"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MedVox"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.local"),
                x509.IPAddress("127.0.0.1"),
                x509.IPAddress("192.168.1.1"),  # Common local IP
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key
        with open("server.crt", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open("server.key", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        print("✅ Self-signed certificate created")
        return True
        
    except ImportError:
        print("❌ cryptography library not available")
        print("Install with: pip install cryptography")
        return False
    except Exception as e:
        print(f"❌ Failed to create certificate: {e}")
        return False

def start_server():
    """Start the HTTPS server"""
    
    # Change to frontend directory
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)
    
    print(f"🦷 MedVox Frontend Server")
    print(f"📁 Serving from: {frontend_dir}")
    print(f"🌐 Host: {HOST}")
    print(f"🔌 Port: {PORT}")
    
    # Check for certificate files
    if not (Path("server.crt").exists() and Path("server.key").exists()):
        print("\n🔐 Creating HTTPS certificate...")
        if not create_self_signed_cert():
            print("\n⚠️  Falling back to HTTP (microphone may not work)")
            use_https = False
        else:
            use_https = True
    else:
        use_https = True
    
    # Create server
    try:
        server = http.server.HTTPServer((HOST, PORT), CORSRequestHandler)
        
        if use_https:
            # Setup SSL
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile="server.crt", keyfile="server.key")
            server.socket = context.wrap_socket(server.socket, server_side=True)
            protocol = "https"
        else:
            protocol = "http"
        
        print(f"\n🚀 Server running at {protocol}://{HOST}:{PORT}")
        print(f"📱 iPad URL: {protocol}://YOUR_COMPUTER_IP:{PORT}")
        print(f"💻 Local URL: {protocol}://localhost:{PORT}")
        
        if use_https:
            print(f"\n⚠️  Browser will show security warning for self-signed certificate")
            print(f"    Click 'Advanced' → 'Proceed to localhost' to continue")
        
        print(f"\n🎤 Microphone access:")
        print(f"    • {'✅ Should work' if use_https else '❌ May not work'} ({'HTTPS' if use_https else 'HTTP'})")
        
        print(f"\n📋 Backend API:")
        print(f"    • Make sure FastAPI server is running on http://localhost:8000")
        print(f"    • Check API endpoint in frontend settings")
        
        print(f"\n🛑 Press Ctrl+C to stop\n")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server() 