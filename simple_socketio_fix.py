#!/usr/bin/env python3
"""
Simple Socket.IO fix for Tailscale VPN packet overflow
Clean approach without breaking existing code
"""

import os
import shutil

def fix_socketio_config():
    """Apply minimal Socket.IO configuration fix"""
    
    app_file = 'app/app.py'
    
    if not os.path.exists(app_file):
        print(f"❌ {app_file} not found")
        return False
    
    # Create backup
    shutil.copy(app_file, 'app/app.py.backup2')
    print("📁 Created backup: app/app.py.backup2")
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if 'ping_timeout=180' in content:
        print("✅ Socket.IO already optimized")
        return True
    
    # Find and replace the Socket.IO initialization
    old_line = 'socketio = SocketIO(app, cors_allowed_origins="*")'
    
    new_config = '''# Socket.IO with VPN optimizations for Tailscale
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        ping_timeout=180,           # Long timeout for VPN latency
        ping_interval=60,           # Less frequent pings
        max_http_buffer_size=500000,  # Smaller buffer to prevent overflow
        transports=['polling'],     # Polling only - more stable over VPN
        engineio_logger=False,
        logger=False
    )'''
    
    if old_line in content:
        content = content.replace(old_line, new_config)
        
        with open(app_file, 'w') as f:
            f.write(content)
        
        print("✅ Socket.IO configuration updated for Tailscale VPN")
        return True
    else:
        print("⚠️  Socket.IO initialization not found in expected format")
        return False

def fix_client_throttling():
    """Apply simple client-side throttling"""
    
    js_file = 'static/app.js'
    
    if not os.path.exists(js_file):
        print(f"❌ {js_file} not found")
        return False
    
    # Create backup
    shutil.copy(js_file, 'static/app.js.backup2')
    print("📁 Created backup: static/app.js.backup2")
    
    with open(js_file, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if 'VPN_THROTTLING' in content:
        print("✅ Client-side throttling already applied")
        return True
    
    # Add simple throttling at the beginning
    throttling_code = '''
// VPN_THROTTLING - Simple audio packet throttling for Tailscale
let lastAudioSend = 0;
const AUDIO_THROTTLE_MS = 100; // Send audio every 100ms instead of ~20ms

function throttledEmit(event, data) {
    if (event === 'audio_data') {
        const now = Date.now();
        if (now - lastAudioSend < AUDIO_THROTTLE_MS) {
            return; // Skip this packet
        }
        lastAudioSend = now;
    }
    
    if (socket && socket.connected) {
        socket.emit(event, data);
    }
}

// Replace socket.emit with throttled version for audio
const originalEmit = function(event, data) {
    throttledEmit(event, data);
};
'''
    
    # Add throttling code at the beginning
    content = throttling_code + '\n' + content
    
    # Replace socket.emit('audio_data' with throttledEmit('audio_data'
    content = content.replace("socket.emit('audio_data'", "throttledEmit('audio_data'")
    
    with open(js_file, 'w') as f:
        f.write(content)
    
    print("✅ Client-side audio throttling applied")
    return True

def main():
    print("🔧 Simple Socket.IO Fix for Tailscale VPN")
    print("=" * 45)
    print("Applying clean fixes without breaking existing code...")
    print()
    
    success_count = 0
    
    # Fix 1: Socket.IO server configuration
    print("🔧 Step 1: Optimizing Socket.IO server configuration...")
    if fix_socketio_config():
        success_count += 1
    
    # Fix 2: Client-side throttling
    print("\n🔧 Step 2: Adding client-side audio throttling...")
    if fix_client_throttling():
        success_count += 1
    
    print(f"\n🎉 Simple Socket.IO Fix Complete!")
    print("=" * 40)
    print(f"✅ {success_count}/2 fixes applied successfully")
    
    if success_count == 2:
        print("\n🔧 What Was Fixed:")
        print("• Server: Extended timeouts and reduced buffer size")
        print("• Client: Audio packets throttled to 100ms intervals")
        print("• Transport: Polling only (more stable over VPN)")
        
        print("\n🚀 Next Steps:")
        print("1. Start server: python app_tailscale_domain.py")
        print("2. Test Tailscale access: https://100.120.44.48:5003")
        print("3. Mobile browsers should work reliably now")
        
        print("\n📱 Expected Results:")
        print("• No more 'Too many packets in payload' errors")
        print("• Stable audio streaming over Tailscale VPN")
        print("• Reliable mobile browser connections")
    else:
        print("\n⚠️  Some fixes failed - check file permissions")
    
    return success_count == 2

if __name__ == '__main__':
    main()
