#!/usr/bin/env python3
"""
Mobile UI Fix for AI Meeting Transcription
Optimizes buttons, controls, and layout for small mobile devices
"""

import os
import shutil

def add_mobile_css():
    """Add comprehensive mobile CSS optimizations"""
    
    mobile_css = '''
/* ========================================
   MOBILE UI OPTIMIZATIONS FOR TAILSCALE
   ======================================== */

/* Mobile-first responsive design */
@media (max-width: 480px) {
    /* Container and layout adjustments */
    .container {
        padding: 0.5rem !important;
        max-width: 100% !important;
    }
    
    /* Header optimizations */
    .header {
        padding: 0.75rem 0.5rem !important;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .session-timer {
        font-size: 0.8rem !important;
        order: 3;
        width: 100%;
        text-align: center;
    }
    
    /* Button optimizations for touch */
    .btn {
        min-height: 44px !important; /* Apple's recommended touch target */
        padding: 0.75rem 1rem !important;
        font-size: 0.9rem !important;
        border-radius: 8px !important;
        margin: 0.25rem !important;
        touch-action: manipulation; /* Prevents zoom on double-tap */
    }
    
    .btn--lg {
        min-height: 52px !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
    }
    
    .btn--sm {
        min-height: 40px !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.8rem !important;
    }
    
    /* Mode tabs for mobile */
    .mode-tabs {
        flex-direction: column !important;
        gap: 0.5rem !important;
        width: 100%;
    }
    
    .mode-tab {
        width: 100% !important;
        min-height: 48px !important;
        justify-content: center !important;
        padding: 0.75rem !important;
    }
    
    /* Control panel mobile layout */
    .control-group {
        flex-direction: column !important;
        gap: 0.75rem !important;
        width: 100%;
    }
    
    .control-group .btn {
        width: 100% !important;
        max-width: none !important;
    }
    
    /* Recording controls - stack vertically */
    #recordButton,
    #pauseButton,
    #stopButton {
        width: 100% !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Secondary controls in a row */
    .control-group .btn--sm {
        width: 48% !important;
        display: inline-block !important;
        margin: 0.25rem 1% !important;
    }
    
    /* Info panel mobile layout */
    .info-panel {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }
    
    .info-item {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.25rem !important;
        padding: 0.5rem !important;
        border: 1px solid var(--color-border) !important;
        border-radius: 6px !important;
    }
    
    .info-label {
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    
    .info-value {
        font-size: 0.9rem !important;
    }
    
    /* Form controls mobile optimization */
    .form-control,
    select.form-control {
        min-height: 44px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important; /* Prevents zoom on iOS */
        border-radius: 8px !important;
        width: 100% !important;
    }
    
    /* Upload zone mobile */
    .upload-zone {
        min-height: 120px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    .upload-zone h3 {
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Transcript area mobile */
    .transcript-content {
        min-height: 200px !important;
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
        padding: 0.75rem !important;
    }
    
    .transcript-header {
        flex-direction: column !important;
        gap: 0.5rem !important;
        align-items: stretch !important;
    }
    
    .transcript-controls {
        display: flex !important;
        gap: 0.5rem !important;
        width: 100% !important;
    }
    
    .transcript-controls .btn {
        flex: 1 !important;
        min-height: 40px !important;
    }
    
    /* Sidebar mobile - convert to bottom sheet style */
    .sidebar {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        top: auto !important;
        max-height: 60vh !important;
        overflow-y: auto !important;
        background: var(--color-surface) !important;
        border-top: 2px solid var(--color-border) !important;
        border-radius: 16px 16px 0 0 !important;
        z-index: 1000 !important;
        transform: translateY(calc(100% - 60px)) !important;
        transition: transform 0.3s ease !important;
    }
    
    .sidebar.expanded {
        transform: translateY(0) !important;
    }
    
    .sidebar::before {
        content: "⬆️ Swipe up for AI tools";
        display: block !important;
        text-align: center !important;
        padding: 1rem !important;
        font-size: 0.8rem !important;
        color: var(--color-text-secondary) !important;
        border-bottom: 1px solid var(--color-border) !important;
        cursor: pointer !important;
    }
    
    /* Sidebar sections mobile */
    .sidebar-section {
        padding: 1rem !important;
        border-bottom: 1px solid var(--color-border) !important;
    }
    
    .sidebar-section h3 {
        font-size: 1rem !important;
        margin-bottom: 0.75rem !important;
    }
    
    /* Modal mobile optimization */
    .modal-content {
        width: 95vw !important;
        max-width: none !important;
        max-height: 90vh !important;
        margin: 5vh auto !important;
        border-radius: 12px !important;
    }
    
    .modal-header {
        padding: 1rem !important;
        border-bottom: 1px solid var(--color-border) !important;
    }
    
    .modal-body {
        padding: 1rem !important;
        max-height: 60vh !important;
        overflow-y: auto !important;
    }
    
    .modal-footer {
        padding: 1rem !important;
        gap: 0.5rem !important;
        flex-direction: column !important;
    }
    
    .modal-footer .btn {
        width: 100% !important;
    }
    
    /* Settings tabs mobile */
    .settings-tabs {
        flex-direction: column !important;
        gap: 0.25rem !important;
    }
    
    .settings-tab {
        width: 100% !important;
        min-height: 44px !important;
        justify-content: flex-start !important;
        padding: 0.75rem 1rem !important;
    }
    
    /* History section mobile */
    .history-content {
        max-height: 300px !important;
        overflow-y: auto !important;
    }
    
    /* No-JS controls mobile */
    .no-js-controls {
        margin-top: 1rem !important;
        padding: 1rem !important;
    }
    
    .no-js-controls > div:last-child {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }
    
    .no-js-controls .btn {
        width: 100% !important;
    }
    
    /* Toast notifications mobile */
    .notification-container {
        top: 10px !important;
        left: 10px !important;
        right: 10px !important;
        max-width: none !important;
    }
    
    .notification {
        margin-bottom: 0.5rem !important;
        padding: 0.75rem !important;
        font-size: 0.9rem !important;
    }
    
    /* Development panel mobile */
    .dev-control-panel {
        bottom: 10px !important;
        right: 10px !important;
        left: 10px !important;
        min-width: auto !important;
    }
    
    /* Accessibility improvements */
    button:focus,
    .btn:focus,
    input:focus,
    select:focus,
    textarea:focus {
        outline: 2px solid var(--color-primary) !important;
        outline-offset: 2px !important;
    }
    
    /* Prevent text selection on buttons */
    .btn,
    button {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    
    /* Improve tap targets */
    .btn-icon {
        margin-right: 0.5rem !important;
        font-size: 1.1em !important;
    }
    
    /* Hide less important elements on very small screens */
    .shortcut-text,
    .feature-status,
    .session-timer {
        display: none !important;
    }
}

/* Extra small devices (phones in portrait) */
@media (max-width: 360px) {
    .btn {
        font-size: 0.8rem !important;
        padding: 0.6rem 0.8rem !important;
    }
    
    .btn--lg {
        font-size: 0.9rem !important;
        padding: 0.8rem 1rem !important;
    }
    
    .container {
        padding: 0.25rem !important;
    }
    
    .sidebar::before {
        font-size: 0.7rem !important;
        padding: 0.75rem !important;
    }
}

/* Landscape orientation adjustments */
@media (max-width: 768px) and (orientation: landscape) {
    .sidebar {
        max-height: 50vh !important;
        transform: translateY(calc(100% - 40px)) !important;
    }
    
    .modal-content {
        max-height: 80vh !important;
    }
    
    .transcript-content {
        min-height: 150px !important;
    }
}
'''
    
    css_file = 'static/style.css'
    
    if not os.path.exists(css_file):
        print(f"❌ {css_file} not found")
        return False
    
    # Create backup
    shutil.copy(css_file, 'static/style.css.mobile_backup')
    print("📁 Created backup: static/style.css.mobile_backup")
    
    with open(css_file, 'r') as f:
        content = f.read()
    
    # Check if mobile CSS already exists
    if 'MOBILE UI OPTIMIZATIONS FOR TAILSCALE' in content:
        print("✅ Mobile CSS already added")
        return True
    
    # Add mobile CSS at the end
    content += '\n' + mobile_css
    
    with open(css_file, 'w') as f:
        f.write(content)
    
    print("✅ Mobile CSS optimizations added")
    return True

def add_mobile_javascript():
    """Add mobile-specific JavaScript enhancements"""
    
    mobile_js = '''
// Mobile UI enhancements for Tailscale access
(function() {
    'use strict';
    
    // Mobile detection
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isSmallScreen = window.innerWidth <= 480;
    
    if (isMobile || isSmallScreen) {
        console.log('📱 Mobile device detected - applying mobile optimizations');
        
        // Add mobile class to body
        document.body.classList.add('mobile-device');
        
        // Sidebar mobile behavior
        function initMobileSidebar() {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                // Add click handler to expand/collapse
                sidebar.addEventListener('click', function(e) {
                    if (e.target === sidebar || e.target.matches('.sidebar::before')) {
                        sidebar.classList.toggle('expanded');
                    }
                });
                
                // Add swipe gesture support
                let startY = 0;
                let currentY = 0;
                
                sidebar.addEventListener('touchstart', function(e) {
                    startY = e.touches[0].clientY;
                });
                
                sidebar.addEventListener('touchmove', function(e) {
                    currentY = e.touches[0].clientY;
                    const diff = startY - currentY;
                    
                    if (diff > 50) { // Swipe up
                        sidebar.classList.add('expanded');
                    } else if (diff < -50) { // Swipe down
                        sidebar.classList.remove('expanded');
                    }
                });
            }
        }
        
        // Improve button touch feedback
        function enhanceButtonFeedback() {
            const buttons = document.querySelectorAll('.btn, button');
            buttons.forEach(button => {
                button.addEventListener('touchstart', function() {
                    this.style.transform = 'scale(0.95)';
                    this.style.opacity = '0.8';
                });
                
                button.addEventListener('touchend', function() {
                    this.style.transform = 'scale(1)';
                    this.style.opacity = '1';
                });
                
                button.addEventListener('touchcancel', function() {
                    this.style.transform = 'scale(1)';
                    this.style.opacity = '1';
                });
            });
        }
        
        // Prevent zoom on input focus (iOS)
        function preventInputZoom() {
            const inputs = document.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.style.fontSize !== '16px') {
                    input.style.fontSize = '16px';
                }
            });
        }
        
        // Auto-hide address bar on scroll
        function autoHideAddressBar() {
            let lastScrollTop = 0;
            window.addEventListener('scroll', function() {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                if (scrollTop > lastScrollTop && scrollTop > 100) {
                    // Scrolling down - try to hide address bar
                    window.scrollTo(0, scrollTop + 1);
                }
                lastScrollTop = scrollTop;
            });
        }
        
        // Initialize mobile features
        document.addEventListener('DOMContentLoaded', function() {
            initMobileSidebar();
            enhanceButtonFeedback();
            preventInputZoom();
            autoHideAddressBar();
            
            console.log('✅ Mobile UI enhancements initialized');
        });
        
        // Handle orientation changes
        window.addEventListener('orientationchange', function() {
            setTimeout(function() {
                // Recalculate layout after orientation change
                window.scrollTo(0, 0);
                
                // Adjust sidebar if needed
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && sidebar.classList.contains('expanded')) {
                    sidebar.classList.remove('expanded');
                }
            }, 100);
        });
    }
})();
'''
    
    js_file = 'static/app.js'
    
    if not os.path.exists(js_file):
        print(f"❌ {js_file} not found")
        return False
    
    # Create backup
    shutil.copy(js_file, 'static/app.js.mobile_backup')
    print("📁 Created backup: static/app.js.mobile_backup")
    
    with open(js_file, 'r') as f:
        content = f.read()
    
    # Check if mobile JS already exists
    if 'Mobile UI enhancements for Tailscale access' in content:
        print("✅ Mobile JavaScript already added")
        return True
    
    # Add mobile JS at the end
    content += '\n' + mobile_js
    
    with open(js_file, 'w') as f:
        f.write(content)
    
    print("✅ Mobile JavaScript enhancements added")
    return True

def main():
    print("📱 Mobile UI Fix for AI Meeting Transcription")
    print("=" * 50)
    print("Optimizing UI for small mobile devices...")
    print()
    
    success_count = 0
    
    # Fix 1: Add mobile CSS
    print("🎨 Step 1: Adding mobile CSS optimizations...")
    if add_mobile_css():
        success_count += 1
    
    # Fix 2: Add mobile JavaScript
    print("\n📱 Step 2: Adding mobile JavaScript enhancements...")
    if add_mobile_javascript():
        success_count += 1
    
    print(f"\n🎉 Mobile UI Fix Complete!")
    print("=" * 40)
    print(f"✅ {success_count}/2 optimizations applied successfully")
    
    if success_count == 2:
        print("\n📱 Mobile Optimizations Applied:")
        print("• Touch-friendly buttons (44px minimum height)")
        print("• Responsive layout for small screens")
        print("• Bottom sheet sidebar for mobile")
        print("• Improved form controls (prevents zoom)")
        print("• Touch feedback and gestures")
        print("• Optimized modals and notifications")
        
        print("\n🚀 Mobile Features:")
        print("• Swipe up/down to expand/collapse sidebar")
        print("• Touch feedback on all buttons")
        print("• Auto-hide address bar on scroll")
        print("• Orientation change handling")
        print("• Prevents accidental zoom on inputs")
        
        print("\n📱 Test on Mobile:")
        print("1. Access: https://100.120.44.48:5003")
        print("2. All buttons should be easily tappable")
        print("3. Sidebar swipes up from bottom")
        print("4. Forms don't cause zoom on focus")
        print("5. Layout adapts to screen size")
    else:
        print("\n⚠️  Some optimizations failed - check file permissions")
    
    return success_count == 2

if __name__ == '__main__':
    main()
