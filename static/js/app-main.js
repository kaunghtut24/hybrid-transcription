// Main Application Entry Point
// This is the new, refactored main application file that imports modular components

// Import all the modular services
// Note: In a production environment, you might want to use ES6 modules or a bundler

class MeetingTranscriptionApp {
    constructor() {
        console.log('🔧 MeetingTranscriptionApp constructor started...');
        
        // Core application state
        this.sessionToken = null;
        this.isRecording = false;
        this.transcript = [];
        this.interimResult = '';
        this.activeTranscriptionService = 'webspeech'; // Default to Web Speech API
        
        // Service instances
        this.webSocketManager = null;
        this.assemblyAIService = null;
        this.geminiService = null;
        this.fileUploadService = null;
        this.languageDetectionService = null;
        
        // UI elements
        this.elements = {};
        
        // Configuration
        this.config = {
            gemini: {
                baseUrl: '/api/gemini',
                model: 'gemini-2.0-flash-exp'
            }
        };
        
        // Initialize the application
        this.init();
    }

    async init() {
        try {
            console.log('🚀 Initializing MeetingTranscriptionApp...');
            
            // Initialize UI elements
            this.initializeElements();
            
            // Create session
            await this.createSession();
            
            // Initialize services
            this.initializeServices();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Load configuration
            await this.loadConfiguration();
            
            console.log('✅ MeetingTranscriptionApp initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize MeetingTranscriptionApp:', error);
            this.showToast('Failed to initialize application', 'error');
        }
    }

    initializeElements() {
        // Cache DOM elements for better performance
        this.elements = {
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            transcriptDiv: document.getElementById('transcript'),
            interimDiv: document.getElementById('interim'),
            statusDiv: document.getElementById('status'),
            serviceStatus: document.getElementById('serviceStatus'),
            summarizeBtn: document.getElementById('summarizeBtn'),
            translateBtn: document.getElementById('translateBtn'),
            exportBtn: document.getElementById('exportBtn'),
            clearBtn: document.getElementById('clearBtn'),
            fileUpload: document.getElementById('fileUpload'),
            uploadBtn: document.getElementById('uploadBtn'),
            languageSelect: document.getElementById('languageSelect'),
            configModal: document.getElementById('configModal'),
            configBtn: document.getElementById('configBtn'),
            saveConfigBtn: document.getElementById('saveConfigBtn'),
            assemblyaiKeyInput: document.getElementById('assemblyaiKey'),
            geminiKeyInput: document.getElementById('geminiKey')
        };
    }

    async createSession() {
        try {
            const response = await fetch('/api/session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to create session: ${response.status}`);
            }

            const data = await response.json();
            this.sessionToken = data.token;
            
            console.log('✅ Session created successfully');
            
        } catch (error) {
            console.error('❌ Failed to create session:', error);
            throw error;
        }
    }

    initializeServices() {
        // Initialize WebSocket Manager
        this.webSocketManager = new UnifiedWebSocketManager(this.sessionToken);
        
        // Initialize Gemini Service
        this.geminiService = new GeminiService(this.sessionToken, this.config.gemini);
        
        // Initialize other services (will be created when needed)
        this.assemblyAIService = null; // Created when AssemblyAI is configured
        this.fileUploadService = null; // Created when needed
        this.languageDetectionService = null; // Created when needed
        
        console.log('✅ Services initialized');
    }

    setupEventListeners() {
        // Recording controls
        if (this.elements.startBtn) {
            this.elements.startBtn.addEventListener('click', () => this.startRecording());
        }
        
        if (this.elements.stopBtn) {
            this.elements.stopBtn.addEventListener('click', () => this.stopRecording());
        }
        
        // AI features
        if (this.elements.summarizeBtn) {
            this.elements.summarizeBtn.addEventListener('click', () => this.summarizeTranscript());
        }
        
        if (this.elements.translateBtn) {
            this.elements.translateBtn.addEventListener('click', () => this.translateTranscript());
        }
        
        // Utility functions
        if (this.elements.exportBtn) {
            this.elements.exportBtn.addEventListener('click', () => this.exportTranscript());
        }
        
        if (this.elements.clearBtn) {
            this.elements.clearBtn.addEventListener('click', () => this.clearTranscript());
        }
        
        // File upload
        if (this.elements.uploadBtn) {
            this.elements.uploadBtn.addEventListener('click', () => this.uploadFile());
        }
        
        // Configuration
        if (this.elements.configBtn) {
            this.elements.configBtn.addEventListener('click', () => this.openConfigModal());
        }
        
        if (this.elements.saveConfigBtn) {
            this.elements.saveConfigBtn.addEventListener('click', () => this.saveConfiguration());
        }
        
        console.log('✅ Event listeners set up');
    }

    async loadConfiguration() {
        try {
            const response = await fetch('/api/config', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const config = await response.json();
                this.updateServiceStatus(config);
                
                // Load custom prompts if Gemini is configured
                if (config.gemini_configured) {
                    await this.geminiService.loadCustomPrompts();
                }
            }
        } catch (error) {
            console.error('Failed to load configuration:', error);
        }
    }

    async startRecording() {
        if (this.isRecording) return;
        
        try {
            this.isRecording = true;
            this.updateUI();
            
            // Try AssemblyAI first if configured, fallback to Web Speech API
            if (this.activeTranscriptionService === 'assemblyai' && this.assemblyAIService) {
                await this.assemblyAIService.startRecording();
            } else {
                await this.startWebSpeechRecording();
            }
            
            this.showToast('Recording started', 'success');
            
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.isRecording = false;
            this.updateUI();
            this.showToast('Failed to start recording', 'error');
        }
    }

    async stopRecording() {
        if (!this.isRecording) return;
        
        try {
            this.isRecording = false;
            this.updateUI();
            
            if (this.activeTranscriptionService === 'assemblyai' && this.assemblyAIService) {
                this.assemblyAIService.stopRecording();
            } else {
                this.stopWebSpeechRecording();
            }
            
            this.showToast('Recording stopped', 'success');
            
        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.showToast('Failed to stop recording', 'error');
        }
    }

    async startWebSpeechRecording() {
        // Web Speech API implementation
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            throw new Error('Speech recognition not supported in this browser');
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscript) {
                this.addTranscriptEntry(finalTranscript, event.results[event.results.length - 1][0].confidence);
            }

            this.updateInterimResult(interimTranscript);
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.showToast(`Speech recognition error: ${event.error}`, 'error');
        };

        this.recognition.onend = () => {
            if (this.isRecording) {
                // Restart recognition if we're still supposed to be recording
                setTimeout(() => {
                    if (this.isRecording) {
                        this.recognition.start();
                    }
                }, 100);
            }
        };

        this.recognition.start();
    }

    stopWebSpeechRecording() {
        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }
    }

    addTranscriptEntry(text, confidence = 1.0, isInterim = false, speaker = null) {
        const entry = {
            text: text.trim(),
            timestamp: new Date().toISOString(),
            confidence: confidence,
            speaker: speaker || 'Speaker',
            isInterim: isInterim
        };

        if (!isInterim) {
            this.transcript.push(entry);
            this.updateTranscriptDisplay();
        }
    }

    updateInterimResult(text, speaker = null) {
        this.interimResult = text;
        if (this.elements.interimDiv) {
            const speakerPrefix = speaker ? `${speaker}: ` : '';
            this.elements.interimDiv.textContent = speakerPrefix + text;
        }
    }

    updateTranscriptDisplay() {
        if (!this.elements.transcriptDiv) return;

        this.elements.transcriptDiv.innerHTML = this.transcript
            .map(entry => `
                <div class="transcript-entry">
                    <span class="speaker">${entry.speaker}:</span>
                    <span class="text">${entry.text}</span>
                    <span class="timestamp">${new Date(entry.timestamp).toLocaleTimeString()}</span>
                </div>
            `).join('');

        // Scroll to bottom
        this.elements.transcriptDiv.scrollTop = this.elements.transcriptDiv.scrollHeight;
    }

    async summarizeTranscript() {
        if (this.transcript.length === 0) {
            this.showToast('No transcript to summarize', 'warning');
            return;
        }

        try {
            this.showToast('Generating summary...', 'info');
            const summary = await this.geminiService.summarizeTranscript(this.transcript);
            this.displaySummary(summary);
            this.showToast('Summary generated successfully', 'success');
        } catch (error) {
            console.error('Failed to generate summary:', error);
            this.showToast('Failed to generate summary', 'error');
        }
    }

    async translateTranscript() {
        if (this.transcript.length === 0) {
            this.showToast('No transcript to translate', 'warning');
            return;
        }

        const targetLanguage = this.elements.languageSelect?.value || 'es';
        const fullText = this.transcript.map(entry => entry.text).join(' ');

        try {
            this.showToast('Translating...', 'info');
            const translation = await this.geminiService.translateText(fullText, targetLanguage);
            this.displayTranslation(translation, targetLanguage);
            this.showToast('Translation completed successfully', 'success');
        } catch (error) {
            console.error('Failed to translate:', error);
            this.showToast('Failed to translate transcript', 'error');
        }
    }

    displaySummary(summary) {
        // Create or update summary display
        let summaryDiv = document.getElementById('summaryResult');
        if (!summaryDiv) {
            summaryDiv = document.createElement('div');
            summaryDiv.id = 'summaryResult';
            summaryDiv.className = 'result-panel';
            document.body.appendChild(summaryDiv);
        }

        summaryDiv.innerHTML = `
            <h3>Meeting Summary</h3>
            <div class="summary-content">${summary}</div>
            <button onclick="this.parentElement.style.display='none'">Close</button>
        `;
        summaryDiv.style.display = 'block';
    }

    displayTranslation(translation, targetLanguage) {
        // Create or update translation display
        let translationDiv = document.getElementById('translationResult');
        if (!translationDiv) {
            translationDiv = document.createElement('div');
            translationDiv.id = 'translationResult';
            translationDiv.className = 'result-panel';
            document.body.appendChild(translationDiv);
        }

        translationDiv.innerHTML = `
            <h3>Translation (${targetLanguage})</h3>
            <div class="translation-content">${translation}</div>
            <button onclick="this.parentElement.style.display='none'">Close</button>
        `;
        translationDiv.style.display = 'block';
    }

    exportTranscript() {
        if (this.transcript.length === 0) {
            this.showToast('No transcript to export', 'warning');
            return;
        }

        const exportData = {
            timestamp: new Date().toISOString(),
            transcript: this.transcript,
            summary: document.getElementById('summaryResult')?.textContent || null,
            translation: document.getElementById('translationResult')?.textContent || null
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transcript-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showToast('Transcript exported successfully', 'success');
    }

    clearTranscript() {
        this.transcript = [];
        this.interimResult = '';
        this.updateTranscriptDisplay();
        if (this.elements.interimDiv) {
            this.elements.interimDiv.textContent = '';
        }
        this.showToast('Transcript cleared', 'info');
    }

    updateUI() {
        if (this.elements.startBtn) {
            this.elements.startBtn.disabled = this.isRecording;
        }
        if (this.elements.stopBtn) {
            this.elements.stopBtn.disabled = !this.isRecording;
        }
        if (this.elements.statusDiv) {
            this.elements.statusDiv.textContent = this.isRecording ? 'Recording...' : 'Ready';
        }
    }

    updateServiceStatus(config = null) {
        if (!this.elements.serviceStatus) return;

        if (config) {
            const status = [];
            if (config.assemblyai_configured) {
                status.push('AssemblyAI: ✅');
                // Initialize AssemblyAI service if not already done
                if (!this.assemblyAIService) {
                    this.assemblyAIService = new AssemblyAIService(null, this);
                    this.activeTranscriptionService = 'assemblyai';
                }
            } else {
                status.push('AssemblyAI: ❌');
            }

            if (config.gemini_configured) {
                status.push('Gemini: ✅');
            } else {
                status.push('Gemini: ❌');
            }

            this.elements.serviceStatus.innerHTML = status.join(' | ');
        }
    }

    openConfigModal() {
        if (this.elements.configModal) {
            this.elements.configModal.style.display = 'block';
        }
    }

    async saveConfiguration() {
        const assemblyaiKey = this.elements.assemblyaiKeyInput?.value.trim();
        const geminiKey = this.elements.geminiKeyInput?.value.trim();

        if (!assemblyaiKey && !geminiKey) {
            this.showToast('Please enter at least one API key', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.sessionToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    assemblyai_key: assemblyaiKey,
                    gemini_key: geminiKey
                })
            });

            if (response.ok) {
                const config = await response.json();
                this.showToast('Configuration saved successfully', 'success');
                this.updateServiceStatus(config);
                
                // Close modal
                if (this.elements.configModal) {
                    this.elements.configModal.style.display = 'none';
                }
                
                // Reload configuration
                await this.loadConfiguration();
            } else {
                const error = await response.json();
                this.showToast(`Failed to save configuration: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.showToast('Failed to save configuration', 'error');
        }
    }

    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Style the toast
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '4px',
            color: 'white',
            fontWeight: 'bold',
            zIndex: '10000',
            maxWidth: '300px',
            wordWrap: 'break-word'
        });

        // Set background color based on type
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        toast.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(toast);

        // Remove toast after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    }

    // Placeholder methods for compatibility
    handleLanguageDetection(data) {
        console.log('Language detected:', data);
    }

    handleLanguageDetectionEvent(data) {
        console.log('Language detection event:', data);
    }

    handleLanguageChange(data) {
        console.log('Language changed:', data);
    }

    handleSpeakerUpdate(speaker) {
        console.log('Speaker update:', speaker);
    }

    handleFileUploadProgress(data) {
        console.log('File upload progress:', data);
    }

    handleFileTranscriptionProgress(data) {
        console.log('File transcription progress:', data);
    }

    handleFileTranscriptionCompleted(data) {
        console.log('File transcription completed:', data);
    }

    handleFileTranscriptionError(data) {
        console.error('File transcription error:', data);
        this.showToast('File transcription failed', 'error');
    }

    async uploadFile() {
        // File upload implementation would go here
        this.showToast('File upload feature coming soon', 'info');
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MeetingTranscriptionApp();
});