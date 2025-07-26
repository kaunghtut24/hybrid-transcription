// AssemblyAI Real-time Transcription Service
class AssemblyAIService {
    constructor(apiKey, app) {
        this.apiKey = apiKey;
        this.app = app;
        this.socket = null;
        this.isConnected = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.sampleRate = 16000;
    }

    async connect() {
        try {
            // Get temporary token for WebSocket connection
            const token = await this.getTemporaryToken();

            // Connect to AssemblyAI WebSocket
            this.socket = new WebSocket(`${this.app.config.assemblyAI.websocketUrl}?token=${token}`);

            this.socket.onopen = () => {
                this.isConnected = true;
                console.log('AssemblyAI WebSocket connected');
                this.app.showToast('AssemblyAI connected', 'success');
            };

            this.socket.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.socket.onerror = (error) => {
                console.error('AssemblyAI WebSocket error:', error);
                this.app.showToast('AssemblyAI connection error', 'error');
                this.fallbackToWebSpeech();
            };

            this.socket.onclose = () => {
                this.isConnected = false;
                console.log('AssemblyAI WebSocket disconnected');
            };

        } catch (error) {
            console.error('Failed to connect to AssemblyAI:', error);
            this.app.showToast('AssemblyAI connection failed', 'error');
            this.fallbackToWebSpeech();
        }
    }

    async getTemporaryToken() {
        // Use Flask backend to securely get AssemblyAI token
        const response = await fetch('/api/assemblyai/token', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.app.sessionToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to get token: ${response.status}`);
        }

        const data = await response.json();
        return data.token;
    }

    async startRecording() {
        try {
            // Get user media
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create audio worklet for processing
            await this.audioContext.audioWorklet.addModule(this.createAudioWorkletProcessor());
            this.processor = new AudioWorkletNode(this.audioContext, 'audio-processor');

            this.processor.port.onmessage = (event) => {
                if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(event.data);
                }
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            // Connect to AssemblyAI
            await this.connect();

        } catch (error) {
            console.error('Failed to start AssemblyAI recording:', error);
            this.app.showToast('Failed to start AssemblyAI recording', 'error');
            this.fallbackToWebSpeech();
        }
    }

    createAudioWorkletProcessor() {
        const processorCode = `
            class AudioProcessor extends AudioWorkletProcessor {
                process(inputs, outputs, parameters) {
                    const input = inputs[0];
                    if (input.length > 0) {
                        const audioData = input[0];
                        // Convert float32 to int16
                        const int16Array = new Int16Array(audioData.length);
                        for (let i = 0; i < audioData.length; i++) {
                            int16Array[i] = Math.max(-32768, Math.min(32767, audioData[i] * 32768));
                        }
                        this.port.postMessage(int16Array.buffer);
                    }
                    return true;
                }
            }
            registerProcessor('audio-processor', AudioProcessor);
        `;

        const blob = new Blob([processorCode], { type: 'application/javascript' });
        return URL.createObjectURL(blob);
    }

    handleMessage(message) {
        if (message.message_type === 'PartialTranscript') {
            this.app.updateInterimResult(message.text);
        } else if (message.message_type === 'FinalTranscript') {
            this.app.addTranscriptEntry(message.text, message.confidence || 0.9, false);
        }
    }

    stopRecording() {
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }

        this.isConnected = false;
    }

    fallbackToWebSpeech() {
        this.app.activeTranscriptionService = 'webspeech';
        this.app.showToast('Switched to Web Speech API', 'warning');
        this.app.updateServiceStatus();
        // The app will handle starting Web Speech API
    }
}

// Google Gemini AI Service
class GeminiService {
    constructor(sessionToken, config) {
        this.sessionToken = sessionToken;
        this.config = config;
        this.baseUrl = config.baseUrl;
        this.model = config.model;
    }

    async generateContent(prompt, systemInstruction = null, retries = 2) {
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const requestBody = {
                    contents: [{
                        parts: [{ text: prompt }]
                    }],
                    generationConfig: {
                        temperature: 0.7,
                        topK: 40,
                        topP: 0.95,
                        maxOutputTokens: 1024,
                    }
                };

                if (systemInstruction) {
                    requestBody.systemInstruction = {
                        parts: [{ text: systemInstruction }]
                    };
                }

                const response = await fetch('/api/gemini/generate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.sessionToken}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: this.model,
                        request_body: requestBody
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Gemini API error: ${response.status} ${response.statusText} - ${errorText}`);
                }

                const data = await response.json();

                if (data.candidates && data.candidates[0] && data.candidates[0].content) {
                    return data.candidates[0].content.parts[0].text;
                } else {
                    throw new Error('Invalid response format from Gemini API');
                }
            } catch (error) {
                console.error(`Gemini API error (attempt ${attempt + 1}):`, error);

                if (attempt === retries) {
                    throw error;
                }

                // Wait before retrying (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
    }

    async summarizeTranscript(transcript) {
        const transcriptText = Array.isArray(transcript)
            ? transcript.map(entry => `${entry.speaker}: ${entry.text}`).join('\n')
            : transcript;

        const prompt = `Please provide a concise summary of the following meeting transcript. Focus on key points, decisions made, and action items:

${transcriptText}

Summary:`;

        const systemInstruction = "You are an expert meeting summarizer. Provide clear, concise summaries that capture the most important information from meeting transcripts.";

        return await this.generateContent(prompt, systemInstruction);
    }

    async translateText(text, targetLanguage) {
        const languageNames = {
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese'
        };

        const targetLangName = languageNames[targetLanguage] || targetLanguage;

        const prompt = `Translate the following text to ${targetLangName}:

${text}

Translation:`;

        const systemInstruction = `You are a professional translator. Provide accurate translations while maintaining the original meaning and context.`;

        return await this.generateContent(prompt, systemInstruction);
    }

    async extractKeywords(transcript) {
        const transcriptText = Array.isArray(transcript)
            ? transcript.map(entry => entry.text).join(' ')
            : transcript;

        const prompt = `Extract the most important keywords and key phrases from the following meeting transcript. Return only the keywords/phrases, separated by commas:

${transcriptText}

Keywords:`;

        const systemInstruction = "You are an expert at extracting key terms and phrases from meeting transcripts. Focus on important topics, decisions, and action items.";

        const result = await this.generateContent(prompt, systemInstruction);

        // Parse the result into an array of keywords
        return result.split(',').map(keyword => keyword.trim()).filter(keyword => keyword.length > 0);
    }
}

// AI Meeting Transcription Assistant Application
class MeetingTranscriptionApp {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.isPaused = false;
        this.startTime = null;
        this.sessionData = {
            sessionId: null,
            startTime: null,
            endTime: null,
            speakers: [],
            transcript: [],
            summary: '',
            keywords: [],
            customDictionary: []
        };
        this.currentSpeaker = null;
        this.speakerCount = 0;
        this.timer = null;
        this.lastSpeechTime = 0;
        this.speakerChangeThreshold = 2000; // 2 seconds

        // API Configuration
        this.config = {
            assemblyAI: {
                apiKey: null,
                websocketUrl: 'wss://api.assemblyai.com/v2/realtime/ws',
                enabled: false
            },
            gemini: {
                apiKey: null,
                baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
                model: 'gemini-2.0-flash-exp',
                enabled: false
            },
            fallback: {
                useWebSpeech: true,
                useSimulation: false
            }
        };

        // Service instances
        this.assemblyAIService = null;
        this.geminiService = null;

        // Session management
        this.sessionToken = null;

        this.activeTranscriptionService = 'webspeech'; // 'assemblyai', 'webspeech'
        this.activeAIService = 'gemini'; // 'gemini', 'simulation'

        this.init();
    }

    async init() {
        this.initElements();
        await this.initSession();
        this.initConfiguration();
        await this.initServices();
        this.initSpeechRecognition();
        this.bindEvents();
        this.loadCustomDictionary();
        this.loadMeetingHistory();
        this.loadSampleData();

        // Initialize UI status indicators
        this.updateServiceStatusIndicators();
        this.updateServiceStatus();
    }

    async initSession() {
        // Create session with Flask backend
        try {
            const response = await fetch('/api/session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionToken = data.token;
                console.log('Session initialized successfully');
            } else {
                console.error('Failed to initialize session');
                this.showToast('Failed to initialize session', 'error');
            }
        } catch (error) {
            console.error('Session initialization error:', error);
            this.showToast('Session initialization failed', 'error');
        }
    }

    initConfiguration() {
        // Load configuration from localStorage
        const savedConfig = localStorage.getItem('meetingApp_config');
        if (savedConfig) {
            try {
                const parsedConfig = JSON.parse(savedConfig);
                // Merge with default config to ensure all properties exist
                this.config = { ...this.config, ...parsedConfig };
            } catch (error) {
                console.error('Failed to parse saved configuration:', error);
            }
        }

        // Enable services if API keys are available
        this.config.assemblyAI.enabled = !!this.config.assemblyAI.apiKey;
        this.config.gemini.enabled = !!this.config.gemini.apiKey;

        // Set active services based on availability
        this.activeTranscriptionService = this.config.assemblyAI.enabled ? 'assemblyai' : 'webspeech';
        this.activeAIService = this.config.gemini.enabled ? 'gemini' : 'simulation';

        console.log('Configuration initialized:', {
            assemblyAI: this.config.assemblyAI.enabled,
            gemini: this.config.gemini.enabled,
            activeTranscription: this.activeTranscriptionService,
            activeAI: this.activeAIService
        });
    }

    getAPIKey(envVarName) {
        // In a real environment, this would access environment variables
        // For browser environment, we'll use a different approach
        return null;
    }

    async initServices() {
        // Initialize AssemblyAI service if enabled
        if (this.config.assemblyAI.enabled) {
            this.assemblyAIService = new AssemblyAIService(this.config.assemblyAI.apiKey, this);
        }

        // Initialize Gemini service if enabled and session token is available
        if (this.config.gemini.enabled && this.sessionToken) {
            this.geminiService = new GeminiService(this.sessionToken, this.config.gemini);
        }

        // Update service status indicators if they exist
        if (this.transcriptionServiceEl && this.aiServiceEl) {
            this.updateServiceStatus();
        }
    }

    initElements() {
        // Control elements
        this.recordButton = document.getElementById('recordButton');
        this.pauseButton = document.getElementById('pauseButton');
        this.stopButton = document.getElementById('stopButton');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.sessionTimer = document.getElementById('sessionTimer');
        this.speakerCountEl = document.getElementById('speakerCount');
        this.languageSelect = document.getElementById('languageSelect');
        this.audioVisualizer = document.getElementById('audioVisualizer');

        // Transcript elements
        this.transcriptContainer = document.getElementById('transcriptContainer');
        this.transcriptPlaceholder = document.getElementById('transcriptPlaceholder');
        this.transcriptContent = document.getElementById('transcriptContent');
        this.clearTranscriptBtn = document.getElementById('clearTranscript');
        this.scrollToBottomBtn = document.getElementById('scrollToBottom');

        // AI features
        this.generateSummaryBtn = document.getElementById('generateSummary');
        this.summaryContent = document.getElementById('summaryContent');
        this.translationTarget = document.getElementById('translationTarget');
        this.translateBtn = document.getElementById('translateText');
        this.translationContent = document.getElementById('translationContent');

        // Keywords
        this.extractKeywordsBtn = document.getElementById('extractKeywords');
        this.highlightKeywordsBtn = document.getElementById('highlightKeywords');
        this.keywordsList = document.getElementById('keywordsList');

        // Dictionary
        this.newWordInput = document.getElementById('newWord');
        this.addWordBtn = document.getElementById('addWord');
        this.dictionaryList = document.getElementById('dictionaryList');

        // Export
        this.exportFormat = document.getElementById('exportFormat');
        this.exportBtn = document.getElementById('exportTranscript');

        // History
        this.toggleHistoryBtn = document.getElementById('toggleHistory');
        this.historyContent = document.getElementById('historyContent');
        this.historySearch = document.getElementById('historySearch');
        this.historyList = document.getElementById('historyList');

        // Modal
        this.modal = document.getElementById('meetingModal');
        this.modalClose = document.getElementById('modalClose');
        this.modalCloseBtn = document.getElementById('modalCloseBtn');
        this.loadMeetingBtn = document.getElementById('loadMeeting');

        // Settings modal elements
        this.settingsBtn = document.getElementById('settingsBtn');
        this.settingsModal = document.getElementById('settingsModal');
        this.settingsModalClose = document.getElementById('settingsModalClose');
        this.settingsModalCancel = document.getElementById('settingsModalCancel');
        this.saveSettingsBtn = document.getElementById('saveSettings');
        this.assemblyaiApiKeyInput = document.getElementById('assemblyaiApiKey');
        this.geminiApiKeyInput = document.getElementById('geminiApiKey');
        this.assemblyaiStatus = document.getElementById('assemblyaiStatus');
        this.geminiStatus = document.getElementById('geminiStatus');

        // Service status indicators
        this.transcriptionServiceEl = document.getElementById('transcriptionService');
        this.aiServiceEl = document.getElementById('aiService');

        // Toast container
        this.toastContainer = document.getElementById('toastContainer');
    }

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = this.languageSelect.value;
            
            this.recognition.onstart = () => {
                this.updateStatus('Recording', 'recording');
                this.audioVisualizer.classList.add('active');
            };

            this.recognition.onresult = (event) => {
                this.handleSpeechResult(event);
            };

            this.recognition.onerror = (event) => {
                this.showToast(`Speech recognition error: ${event.error}`, 'error');
                this.stopRecording();
            };

            this.recognition.onend = () => {
                if (this.isRecording && !this.isPaused) {
                    this.recognition.start(); // Restart for continuous recognition
                }
            };
        } else {
            this.showToast('Speech recognition not supported in this browser', 'error');
            this.recordButton.disabled = true;
        }
    }

    bindEvents() {
        // Control buttons
        this.recordButton.addEventListener('click', () => this.toggleRecording());
        this.pauseButton.addEventListener('click', () => this.pauseRecording());
        this.stopButton.addEventListener('click', () => this.stopRecording());

        // Language change
        this.languageSelect.addEventListener('change', () => {
            if (this.recognition) {
                this.recognition.lang = this.languageSelect.value;
            }
        });

        // Transcript controls
        this.clearTranscriptBtn.addEventListener('click', () => this.clearTranscript());
        this.scrollToBottomBtn.addEventListener('click', () => this.scrollToBottom());

        // AI features
        this.generateSummaryBtn.addEventListener('click', () => this.generateSummary());
        this.translateBtn.addEventListener('click', () => this.translateTranscript());
        this.extractKeywordsBtn.addEventListener('click', () => this.extractKeywords());
        this.highlightKeywordsBtn.addEventListener('click', () => this.highlightKeywords());

        // Dictionary
        this.addWordBtn.addEventListener('click', () => this.addCustomWord());
        this.newWordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addCustomWord();
        });

        // Export
        this.exportBtn.addEventListener('click', () => this.exportTranscript());

        // History
        this.toggleHistoryBtn.addEventListener('click', () => this.toggleHistory());
        this.historySearch.addEventListener('input', () => this.filterHistory());

        // Modal
        this.modalClose.addEventListener('click', () => this.closeModal());
        this.modalCloseBtn.addEventListener('click', () => this.closeModal());
        this.loadMeetingBtn.addEventListener('click', () => this.loadSelectedMeeting());

        // Settings modal
        this.settingsBtn.addEventListener('click', () => this.openSettingsModal());
        this.settingsModalClose.addEventListener('click', () => this.closeSettingsModal());
        this.settingsModalCancel.addEventListener('click', () => this.closeSettingsModal());
        this.saveSettingsBtn.addEventListener('click', () => this.saveSettings());

        // Click outside modal to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.closeModal();
        });

        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) this.closeSettingsModal();
        });
    }

    toggleRecording() {
        if (!this.isRecording) {
            this.startRecording();
        } else {
            this.stopRecording();
        }
    }

    async startRecording() {
        this.isRecording = true;
        this.isPaused = false;
        this.startTime = new Date();
        this.sessionData.sessionId = `meeting-${Date.now()}`;
        this.sessionData.startTime = this.startTime;
        this.sessionData.transcript = [];

        try {
            // Try AssemblyAI first if available
            if (this.activeTranscriptionService === 'assemblyai' && this.assemblyAIService) {
                await this.assemblyAIService.startRecording();
                this.showToast('Recording started with AssemblyAI', 'success');
            } else {
                // Fallback to Web Speech API
                if (!this.recognition) {
                    this.showToast('No transcription service available', 'error');
                    this.isRecording = false;
                    return;
                }
                this.recognition.start();
                this.showToast('Recording started with Web Speech API', 'success');
            }

            this.startTimer();
            this.updateButtons();
            this.transcriptPlaceholder.style.display = 'none';

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showToast('Failed to start recording', 'error');
            this.isRecording = false;

            // Try fallback if AssemblyAI failed
            if (this.activeTranscriptionService === 'assemblyai') {
                this.activeTranscriptionService = 'webspeech';
                this.showToast('Switching to Web Speech API', 'warning');
                setTimeout(() => this.startRecording(), 1000);
            }
        }
    }

    pauseRecording() {
        if (!this.isRecording) return;

        this.isPaused = !this.isPaused;
        
        if (this.isPaused) {
            this.recognition.stop();
            this.updateStatus('Paused', 'paused');
            this.audioVisualizer.classList.remove('active');
            this.showToast('Recording paused', 'warning');
        } else {
            this.recognition.start();
            this.updateStatus('Recording', 'recording');
            this.audioVisualizer.classList.add('active');
            this.showToast('Recording resumed', 'success');
        }
        
        this.updateButtons();
    }

    stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;
        this.isPaused = false;

        // Stop the active transcription service
        if (this.activeTranscriptionService === 'assemblyai' && this.assemblyAIService) {
            this.assemblyAIService.stopRecording();
        } else if (this.recognition) {
            this.recognition.stop();
        }

        this.stopTimer();
        this.sessionData.endTime = new Date();

        this.updateStatus('Ready', 'ready');
        this.audioVisualizer.classList.remove('active');
        this.updateButtons();

        this.saveMeetingToHistory();
        this.showToast('Recording stopped', 'info');
    }

    handleSpeechResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            const confidence = event.results[i][0].confidence;

            if (event.results[i].isFinal) {
                finalTranscript += transcript;
                this.addTranscriptEntry(transcript, confidence, false);
            } else {
                interimTranscript += transcript;
                this.updateInterimResult(transcript);
            }
        }

        this.detectSpeakerChange();
    }

    detectSpeakerChange() {
        const now = Date.now();
        if (now - this.lastSpeechTime > this.speakerChangeThreshold) {
            this.currentSpeaker = this.getNextSpeaker();
        }
        this.lastSpeechTime = now;
    }

    getNextSpeaker() {
        if (!this.currentSpeaker) {
            this.speakerCount = 1;
            this.currentSpeaker = `Speaker ${this.speakerCount}`;
        } else {
            // Simple speaker detection based on silence patterns
            const shouldChangeSpeaker = Math.random() > 0.7; // Simulate speaker detection
            if (shouldChangeSpeaker) {
                this.speakerCount++;
                this.currentSpeaker = `Speaker ${Math.min(this.speakerCount, 5)}`;
            }
        }
        
        this.speakerCountEl.textContent = Math.min(this.speakerCount, 5);
        return this.currentSpeaker;
    }

    addTranscriptEntry(text, confidence, isInterim = false) {
        const timestamp = new Date();
        const entry = {
            timestamp: timestamp.toISOString(),
            speaker: this.currentSpeaker || 'Speaker 1',
            text: text.trim(),
            confidence: confidence || 0.8,
            interim: isInterim
        };

        if (!isInterim) {
            this.sessionData.transcript.push(entry);
        }

        this.renderTranscriptEntry(entry);
    }

    renderTranscriptEntry(entry) {
        const entryEl = document.createElement('div');
        entryEl.className = `transcript-entry ${entry.interim ? 'interim' : ''} ${this.getSpeakerClass(entry.speaker)}`;
        
        const timestamp = new Date(entry.timestamp);
        const timeString = timestamp.toLocaleTimeString();
        
        entryEl.innerHTML = `
            <div class="transcript-timestamp">${timeString}</div>
            <div class="transcript-speaker">${entry.speaker}:</div>
            <div class="transcript-text">${entry.text}
                <span class="confidence-indicator ${this.getConfidenceClass(entry.confidence)}"></span>
            </div>
        `;

        if (entry.interim) {
            // Update or add interim result
            const existingInterim = this.transcriptContent.querySelector('.transcript-entry.interim');
            if (existingInterim) {
                existingInterim.replaceWith(entryEl);
            } else {
                this.transcriptContent.appendChild(entryEl);
            }
        } else {
            // Remove any interim results and add final result
            const interimResults = this.transcriptContent.querySelectorAll('.transcript-entry.interim');
            interimResults.forEach(el => el.remove());
            this.transcriptContent.appendChild(entryEl);
        }

        this.scrollToBottom();
    }

    updateInterimResult(text) {
        if (!text.trim()) return;
        
        const entry = {
            timestamp: new Date().toISOString(),
            speaker: this.currentSpeaker || 'Speaker 1',
            text: text.trim(),
            confidence: 0.5,
            interim: true
        };

        this.renderTranscriptEntry(entry);
    }

    getSpeakerClass(speaker) {
        const speakerNum = parseInt(speaker.match(/\d+/)[0]);
        return `speaker-${Math.min(speakerNum, 5)}`;
    }

    getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'confidence-high';
        if (confidence >= 0.6) return 'confidence-medium';
        return 'confidence-low';
    }

    startTimer() {
        this.timer = setInterval(() => {
            const elapsed = Date.now() - this.startTime.getTime();
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            
            this.sessionTimer.textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    updateStatus(text, status) {
        this.statusText.textContent = text;
        this.statusIndicator.className = `status-indicator ${status}`;
    }

    updateButtons() {
        if (this.isRecording) {
            this.recordButton.innerHTML = '<span class="btn-icon">⏹️</span>Stop Recording';
            this.recordButton.className = 'btn btn--error btn--lg';
            this.pauseButton.disabled = false;
            this.stopButton.disabled = false;
        } else {
            this.recordButton.innerHTML = '<span class="btn-icon">🎤</span>Start Recording';
            this.recordButton.className = 'btn btn--primary btn--lg';
            this.pauseButton.disabled = true;
            this.stopButton.disabled = true;
        }

        if (this.isPaused) {
            this.pauseButton.innerHTML = '<span class="btn-icon">▶️</span>Resume';
        } else {
            this.pauseButton.innerHTML = '<span class="btn-icon">⏸️</span>Pause';
        }
    }

    clearTranscript() {
        this.transcriptContent.innerHTML = '';
        this.sessionData.transcript = [];
        this.transcriptPlaceholder.style.display = 'flex';
        this.showToast('Transcript cleared', 'info');
    }

    scrollToBottom() {
        this.transcriptContainer.scrollTop = this.transcriptContainer.scrollHeight;
    }

    async generateSummary() {
        if (this.sessionData.transcript.length === 0) {
            this.showToast('No transcript available to summarize', 'warning');
            return;
        }

        this.generateSummaryBtn.classList.add('loading');

        try {
            let summary;

            if (this.activeAIService === 'gemini' && this.geminiService) {
                // Use Gemini AI for summarization
                summary = await this.geminiService.summarizeTranscript(this.sessionData.transcript);
                this.showToast('Summary generated with Gemini AI', 'success');
            } else {
                // Fallback to simulation
                summary = this.simulateAISummary();
                this.showToast('Summary generated (simulation)', 'warning');
            }

            this.sessionData.summary = summary;
            this.summaryContent.innerHTML = `<p>${summary}</p>`;

        } catch (error) {
            console.error('Failed to generate summary:', error);

            // Fallback to simulation on error
            if (this.activeAIService === 'gemini') {
                this.activeAIService = 'simulation';
                this.showToast('Gemini AI failed, using fallback', 'warning');

                const summary = this.simulateAISummary();
                this.sessionData.summary = summary;
                this.summaryContent.innerHTML = `<p>${summary}</p>`;
            } else {
                this.showToast('Failed to generate summary', 'error');
            }
        } finally {
            this.generateSummaryBtn.classList.remove('loading');
        }
    }

    simulateAISummary() {
        const transcriptText = this.sessionData.transcript.map(entry => entry.text).join(' ');
        const wordCount = transcriptText.split(' ').length;

        if (wordCount < 50) {
            return 'Brief discussion covering key topics and initial thoughts.';
        } else if (wordCount < 200) {
            return 'Meeting covered several important topics with active participation from team members. Key decisions were made regarding project direction and next steps.';
        } else {
            return 'Comprehensive meeting discussion with detailed analysis of current projects, performance metrics, and strategic planning. Multiple speakers contributed valuable insights and actionable items were identified for follow-up.';
        }
    }

    async translateTranscript() {
        const targetLang = this.translationTarget.value;
        if (!targetLang) {
            this.showToast('Please select a target language', 'warning');
            return;
        }

        if (this.sessionData.transcript.length === 0) {
            this.showToast('No transcript available to translate', 'warning');
            return;
        }

        this.translateBtn.classList.add('loading');

        try {
            let translation;

            if (this.activeAIService === 'gemini' && this.geminiService) {
                // Use Gemini AI for translation
                const transcriptText = this.sessionData.transcript.map(entry => `${entry.speaker}: ${entry.text}`).join('\n');
                const translatedText = await this.geminiService.translateText(transcriptText, targetLang);

                translation = `<div class="translation-entry">
                    <strong>Translation (${targetLang.toUpperCase()}) - Gemini AI:</strong>
                    <p>${translatedText}</p>
                </div>`;

                this.showToast('Translation completed with Gemini AI', 'success');
            } else {
                // Fallback to simulation
                translation = this.simulateTranslation(targetLang);
                this.showToast('Translation completed (simulation)', 'warning');
            }

            this.translationContent.innerHTML = translation;

        } catch (error) {
            console.error('Failed to translate:', error);

            // Fallback to simulation on error
            if (this.activeAIService === 'gemini') {
                this.showToast('Gemini AI failed, using fallback', 'warning');
                const translation = this.simulateTranslation(targetLang);
                this.translationContent.innerHTML = translation;
            } else {
                this.showToast('Failed to translate text', 'error');
            }
        } finally {
            this.translateBtn.classList.remove('loading');
        }
    }

    simulateTranslation(targetLang) {
        const translations = {
            'es': 'Reunión sobre estrategia de producto con métricas positivas de participación del usuario.',
            'fr': 'Réunion sur la stratégie produit avec des métriques d\'engagement utilisateur positives.',
            'de': 'Meeting zur Produktstrategie mit positiven Benutzerengagement-Metriken.',
            'it': 'Riunione sulla strategia del prodotto con metriche di coinvolgimento degli utenti positive.',
            'pt': 'Reunião sobre estratégia de produto com métricas positivas de engajamento do usuário.',
            'ja': '肯定的なユーザーエンゲージメントメトリクスを持つ製品戦略についての会議。',
            'ko': '긍정적인 사용자 참여 지표를 가진 제품 전략 회의.',
            'zh': '关于产品策略的会议，用户参与度指标积极。'
        };

        return `<div class="translation-entry">
            <strong>Translation (${targetLang.toUpperCase()}):</strong>
            <p>${translations[targetLang] || 'Translation not available for this language.'}</p>
        </div>`;
    }

    async extractKeywords() {
        if (this.sessionData.transcript.length === 0) {
            this.showToast('No transcript available for keyword extraction', 'warning');
            return;
        }

        this.extractKeywordsBtn.classList.add('loading');

        try {
            let keywords;

            if (this.activeAIService === 'gemini' && this.geminiService) {
                // Use Gemini AI for keyword extraction
                keywords = await this.geminiService.extractKeywords(this.sessionData.transcript);
                this.showToast('Keywords extracted with Gemini AI', 'success');
            } else {
                // Fallback to simulation
                keywords = this.simulateKeywordExtraction();
                this.showToast('Keywords extracted (simulation)', 'warning');
            }

            this.sessionData.keywords = keywords;
            this.displayKeywords(keywords);

        } catch (error) {
            console.error('Failed to extract keywords:', error);

            // Fallback to simulation on error
            if (this.activeAIService === 'gemini') {
                this.showToast('Gemini AI failed, using fallback', 'warning');
                const keywords = this.simulateKeywordExtraction();
                this.sessionData.keywords = keywords;
                this.displayKeywords(keywords);
            } else {
                this.showToast('Failed to extract keywords', 'error');
            }
        } finally {
            this.extractKeywordsBtn.classList.remove('loading');
        }
    }

    simulateKeywordExtraction() {
        const sampleKeywords = ['product strategy', 'user engagement', 'metrics', 'quarterly review', 'conversion rates', 'analytics', 'dashboard', 'performance', 'retention'];
        return sampleKeywords.slice(0, Math.floor(Math.random() * 4) + 3);
    }

    displayKeywords(keywords) {
        this.keywordsList.innerHTML = keywords.map(keyword => 
            `<span class="keyword-tag">${keyword}</span>`
        ).join('');
    }

    highlightKeywords() {
        if (this.sessionData.keywords.length === 0) {
            this.showToast('Extract keywords first', 'warning');
            return;
        }

        const transcriptEntries = this.transcriptContent.querySelectorAll('.transcript-text');
        
        transcriptEntries.forEach(entry => {
            let text = entry.innerHTML;
            
            this.sessionData.keywords.forEach(keyword => {
                const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
                text = text.replace(regex, `<span class="highlighted">${keyword}</span>`);
            });
            
            entry.innerHTML = text;
        });

        this.showToast('Keywords highlighted in transcript', 'success');
    }

    addCustomWord() {
        const word = this.newWordInput.value.trim();
        if (!word) return;

        if (!this.sessionData.customDictionary.includes(word)) {
            this.sessionData.customDictionary.push(word);
            this.saveCustomDictionary();
            this.renderDictionary();
            this.newWordInput.value = '';
            this.showToast(`Added "${word}" to dictionary`, 'success');
        } else {
            this.showToast('Word already in dictionary', 'warning');
        }
    }

    removeCustomWord(word) {
        const index = this.sessionData.customDictionary.indexOf(word);
        if (index > -1) {
            this.sessionData.customDictionary.splice(index, 1);
            this.saveCustomDictionary();
            this.renderDictionary();
            this.showToast(`Removed "${word}" from dictionary`, 'info');
        }
    }

    renderDictionary() {
        if (this.sessionData.customDictionary.length === 0) {
            this.dictionaryList.innerHTML = '<p class="text-muted">No custom words added yet</p>';
            return;
        }

        this.dictionaryList.innerHTML = this.sessionData.customDictionary.map(word => `
            <div class="dictionary-item">
                <span>${word}</span>
                <span class="dictionary-remove" onclick="app.removeCustomWord('${word}')">&times;</span>
            </div>
        `).join('');
    }

    loadCustomDictionary() {
        // Load sample dictionary
        this.sessionData.customDictionary = [
            'API', 'SaaS', 'KPI', 'ROI', 'Analytics', 'Dashboard', 'Microservice', 'Authentication', 'Database', 'Frontend'
        ];
        this.renderDictionary();
    }

    saveCustomDictionary() {
        // In a real app, this would save to localStorage or a server
        console.log('Custom dictionary saved:', this.sessionData.customDictionary);
    }

    exportTranscript() {
        const format = this.exportFormat.value;
        const data = this.generateExportData(format);
        this.downloadFile(data, `meeting-transcript-${Date.now()}.${format}`, format);
        this.showToast(`Transcript exported as ${format.toUpperCase()}`, 'success');
    }

    generateExportData(format) {
        switch (format) {
            case 'txt':
                return this.sessionData.transcript.map(entry => 
                    `[${new Date(entry.timestamp).toLocaleTimeString()}] ${entry.speaker}: ${entry.text}`
                ).join('\n');
            
            case 'json':
                return JSON.stringify(this.sessionData, null, 2);
            
            case 'pdf':
                return 'PDF export would require a PDF library in a real implementation';
            
            case 'docx':
                return 'DOCX export would require a Word document library in a real implementation';
            
            default:
                return JSON.stringify(this.sessionData, null, 2);
        }
    }

    downloadFile(content, filename, format) {
        const blob = new Blob([content], { 
            type: format === 'json' ? 'application/json' : 'text/plain' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    loadMeetingHistory() {
        const sampleHistory = [
            {
                id: 'meeting-001',
                title: 'Product Strategy Discussion',
                date: '2025-07-26',
                duration: '45 minutes',
                participants: 3
            },
            {
                id: 'meeting-002',
                title: 'Engineering Standup',
                date: '2025-07-25',
                duration: '30 minutes',
                participants: 5
            },
            {
                id: 'meeting-003',
                title: 'Client Requirements Review',
                date: '2025-07-24',
                duration: '60 minutes',
                participants: 4
            }
        ];

        this.renderHistory(sampleHistory);
    }

    renderHistory(meetings) {
        this.historyList.innerHTML = meetings.map(meeting => `
            <div class="history-item" onclick="app.showMeetingDetails('${meeting.id}')">
                <div class="history-item-info">
                    <h4>${meeting.title}</h4>
                    <div class="history-item-meta">
                        ${meeting.date} • ${meeting.duration} • ${meeting.participants} participants
                    </div>
                </div>
            </div>
        `).join('');
    }

    toggleHistory() {
        const isVisible = this.historyContent.style.display !== 'none';
        this.historyContent.style.display = isVisible ? 'none' : 'block';
        this.toggleHistoryBtn.textContent = isVisible ? 'Show History' : 'Hide History';
    }

    filterHistory() {
        const searchTerm = this.historySearch.value.toLowerCase();
        const historyItems = this.historyList.querySelectorAll('.history-item');
        
        historyItems.forEach(item => {
            const title = item.querySelector('h4').textContent.toLowerCase();
            const visible = title.includes(searchTerm);
            item.style.display = visible ? 'flex' : 'none';
        });
    }

    showMeetingDetails(meetingId) {
        // Load sample meeting data
        const sampleMeeting = {
            sessionId: "meeting-001",
            title: "Product Strategy Discussion", 
            startTime: "2025-07-26T10:00:00Z",
            participants: ["John Smith", "Sarah Johnson", "Mike Chen"],
            transcript: [
                {
                    timestamp: "10:00:15",
                    speaker: "John Smith",
                    text: "Good morning everyone, let's start with our quarterly product review.",
                    confidence: 0.95
                },
                {
                    timestamp: "10:00:22",
                    speaker: "Sarah Johnson",
                    text: "Thanks John. I'd like to discuss our user engagement metrics first.",
                    confidence: 0.92
                }
            ]
        };

        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <h4>${sampleMeeting.title}</h4>
            <p><strong>Date:</strong> ${new Date(sampleMeeting.startTime).toLocaleDateString()}</p>
            <p><strong>Participants:</strong> ${sampleMeeting.participants.join(', ')}</p>
            <p><strong>Transcript Preview:</strong></p>
            <div style="max-height: 200px; overflow-y: auto; border: 1px solid var(--color-border); padding: var(--space-12); border-radius: var(--radius-base);">
                ${sampleMeeting.transcript.map(entry => `
                    <p><strong>${entry.speaker}:</strong> ${entry.text}</p>
                `).join('')}
            </div>
        `;

        this.modal.classList.remove('hidden');
        this.selectedMeetingId = meetingId;
    }

    loadSelectedMeeting() {
        this.showToast('Meeting loaded successfully', 'success');
        this.closeModal();
        // In a real app, this would load the meeting data into the current session
    }

    closeModal() {
        this.modal.classList.add('hidden');
    }

    saveMeetingToHistory() {
        // In a real app, this would save to localStorage or a server
        console.log('Meeting saved to history:', this.sessionData);
    }

    loadSampleData() {
        // Load sample transcript for demonstration
        const sampleData = [
            {
                timestamp: new Date().toISOString(),
                speaker: "John Smith",
                text: "Good morning everyone, let's start with our quarterly product review.",
                confidence: 0.95
            },
            {
                timestamp: new Date().toISOString(),
                speaker: "Sarah Johnson",
                text: "Thanks John. I'd like to discuss our user engagement metrics first.",
                confidence: 0.92
            }
        ];

        // Show sample data in summary
        this.summaryContent.innerHTML = '<p>Team discussed quarterly product performance with positive user engagement metrics showing 15% retention increase and 8.5% conversion improvement from new dashboard feature.</p>';
        
        // Show sample keywords
        this.displayKeywords(['quarterly review', 'user engagement', 'retention', 'conversion rates']);
    }

    // Settings Modal Methods
    openSettingsModal() {
        // Load current settings
        this.assemblyaiApiKeyInput.value = this.config.assemblyAI.apiKey || '';
        this.geminiApiKeyInput.value = this.config.gemini.apiKey || '';

        // Update status indicators
        this.updateServiceStatusIndicators();

        this.settingsModal.classList.remove('hidden');
    }

    closeSettingsModal() {
        this.settingsModal.classList.add('hidden');
    }

    async saveSettings() {
        const assemblyaiKey = this.assemblyaiApiKeyInput.value.trim();
        const geminiKey = this.geminiApiKeyInput.value.trim();

        try {
            // Save configuration to Flask backend
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
                const data = await response.json();

                // Update local configuration
                this.config.assemblyAI.enabled = data.assemblyai_configured;
                this.config.gemini.enabled = data.gemini_configured;

                // Set active services based on availability
                this.activeTranscriptionService = this.config.assemblyAI.enabled ? 'assemblyai' : 'webspeech';
                this.activeAIService = this.config.gemini.enabled ? 'gemini' : 'simulation';

                // Reinitialize services
                await this.initServices();

                // Update UI
                this.updateServiceStatusIndicators();
                this.updateServiceStatus();

                this.closeSettingsModal();
                this.showToast('Settings saved successfully', 'success');
            } else {
                const error = await response.json();
                this.showToast(error.error || 'Failed to save settings', 'error');
            }
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showToast('Failed to save settings', 'error');
        }
    }

    updateServiceStatusIndicators() {
        // AssemblyAI status
        if (this.config.assemblyAI.enabled && this.config.assemblyAI.apiKey) {
            this.assemblyaiStatus.textContent = 'Configured';
            this.assemblyaiStatus.className = 'status-badge configured';
        } else {
            this.assemblyaiStatus.textContent = 'Not Configured';
            this.assemblyaiStatus.className = 'status-badge not-configured';
        }

        // Gemini status
        if (this.config.gemini.enabled && this.config.gemini.apiKey) {
            this.geminiStatus.textContent = 'Configured';
            this.geminiStatus.className = 'status-badge configured';
        } else {
            this.geminiStatus.textContent = 'Not Configured';
            this.geminiStatus.className = 'status-badge not-configured';
        }
    }

    updateServiceStatus() {
        // Update transcription service indicator
        if (this.activeTranscriptionService === 'assemblyai') {
            this.transcriptionServiceEl.textContent = 'AssemblyAI';
            this.transcriptionServiceEl.className = 'service-indicator active';
        } else {
            this.transcriptionServiceEl.textContent = 'Web Speech';
            this.transcriptionServiceEl.className = 'service-indicator fallback';
        }

        // Update AI service indicator
        if (this.activeAIService === 'gemini') {
            this.aiServiceEl.textContent = 'Gemini AI';
            this.aiServiceEl.className = 'service-indicator active';
        } else {
            this.aiServiceEl.textContent = 'Simulation';
            this.aiServiceEl.className = 'service-indicator fallback';
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        
        this.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 4000);
    }
}

// Initialize the application
const app = new MeetingTranscriptionApp();