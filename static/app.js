
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

// Compatibility layer for the refactored application
// This file maintains backward compatibility while using the new modular structure

// Re-export classes for backward compatibility
if (typeof window !== 'undefined') {
    // Make sure all the modular components are available globally
    window.UnifiedWebSocketManager = window.UnifiedWebSocketManager || class {};
    window.AssemblyAIService = window.AssemblyAIService || class {};
    window.GeminiService = window.GeminiService || class {};
    
    // Legacy compatibility - redirect to new app instance
    window.MeetingTranscriptionApp = window.MeetingTranscriptionApp || class {};
}

// Simple compatibility shim
console.log('📦 Refactored app.js compatibility layer loaded');
console.log('🔄 Using modular components from static/js/ directory');

// If the new app hasn't been initialized yet, provide a fallback
if (typeof window !== 'undefined' && !window.app) {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.app && window.MeetingTranscriptionApp) {
            console.log('🔧 Initializing app from compatibility layer');
            window.app = new window.MeetingTranscriptionApp();
        }
    });
}

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
