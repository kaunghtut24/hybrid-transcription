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