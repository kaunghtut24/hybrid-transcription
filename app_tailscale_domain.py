#!/usr/bin/env python3
"""
HTTPS Flask app for Tailscale + Domain access
Perfect solution combining VPN security with custom domain
"""

import ssl
import socket
from app.app import create_app

def main():
    """Run Flask app with HTTPS for Tailscale + Domain access"""
    app, socketio = create_app()
    
    # SSL certificate paths
    cert_file = 'tailscale_domain_cert.pem'
    key_file = 'tailscale_domain_key.pem'
    
    # Check if certificates exist
    import os
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("❌ SSL certificates not found!")
        print("Run: python setup_tailscale_domain.py")
        return
    
    print("🔐 Starting HTTPS server for Tailscale + Domain access...")
    print("=" * 65)
    print(f"🌐 Tailscale IP: 100.120.44.48")
    print(f"🏠 Local IP: 192.168.1.11")
    print(f"🌍 Domain: hybrid.mmllm.online")
    print(f"📁 Certificate: {cert_file}")
    print(f"🔑 Private Key: {key_file}")
    print()
    
    print("🌍 Access URLs:")
    print(f"   🌐 Tailscale: https://100.120.44.48:5003")
    print(f"   🏠 Local: https://192.168.1.11:5003")
    print(f"   🌍 Domain: https://hybrid.mmllm.online:5003")
    print(f"   🖥️  Localhost: https://127.0.0.1:5003")
    print()
    
    print("📱 Mobile Access Options:")
    print("=" * 25)
    print("🔥 BEST: Tailscale (No Port Forwarding!)")
    print("1. Install Tailscale on mobile")
    print("2. Connect to same network")
    print(f"3. Open: https://100.120.44.48:5003")
    print("4. Accept certificate → Full microphone access! 🎤")
    print()
    print("🌐 Alternative: Domain (Requires Port Forwarding)")
    print("1. Configure router: 8443 → 5003")
    print("2. Update Cloudflare DNS if needed")
    print("3. Open: https://hybrid.mmllm.online:8443")
    print()
    
    print("✅ Benefits:")
    print("   🎤 Full microphone access on mobile")
    print("   🔒 Secure HTTPS connection")
    print("   🌐 Multiple access methods")
    print("   📱 Works on all mobile browsers")
    print("   🚫 Tailscale = No port forwarding needed!")
    print()
    
    print("🚀 Server starting on port 5003...")
    print("Press Ctrl+C to stop")
    print("=" * 65)
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    
    # Run HTTPS server on port 5003
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5003,
            ssl_context=context,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == '__main__':
    main()
