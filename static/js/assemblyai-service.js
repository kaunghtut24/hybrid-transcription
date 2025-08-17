// AssemblyAI Real-time Transcription Service using SocketIO
class AssemblyAIService {
    constructor(apiKey, app) {
        this.apiKey = apiKey;
        this.app = app;
        this.socketio = null;
        this.isConnected = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.sampleRate = 16000;
        this.sessionId = null;
    }

    async connect() {
        try {
            const validation = await this.validateApiKey();

            if (validation.valid) {
                this.socketio = io();
                this.sessionId = `session_${Date.now()}`;
                this.setupSocketIOListeners();
                this.socketio.emit('join_session', { session_id: this.sessionId });
                this.socketio.emit('start_assemblyai_stream', {
                    session_token: this.app.sessionToken,
                    session_id: this.sessionId
                });
                this.app.showToast('Connecting to AssemblyAI...', 'info');
            }
        } catch (error) {
            console.error('Failed to connect to AssemblyAI:', error);
            this.app.showToast('AssemblyAI connection failed - using Web Speech fallback', 'error');
            this.fallbackToWebSpeech();
        }
    }

    setupSocketIOListeners() {
        this.socketio.on('assemblyai_connected', (data) => {
            this.isConnected = true;
            this.app.showToast('AssemblyAI connected successfully!', 'success');
        });

        this.socketio.on('assemblyai_transcript', (data) => {
            if (data.speaker) {
                this.app.handleSpeakerUpdate(data.speaker);
            }

            if (data.is_final) {
                this.app.addTranscriptEntry(data.transcript, data.confidence, false, data.speaker);
            } else {
                this.app.updateInterimResult(data.transcript, data.speaker);
            }
        });

        this.socketio.on('language_detected', (data) => {
            this.app.handleLanguageDetection(data);
        });

        this.socketio.on('language_detection_event', (data) => {
            this.app.handleLanguageDetectionEvent(data);
        });

        this.socketio.on('language_change_detected', (data) => {
            this.app.handleLanguageChange(data);
        });

        this.socketio.on('language_changed', (data) => {
            this.app.handleLanguageChange(data);
        });

        this.socketio.on('file_upload_progress', (data) => {
            this.app.handleFileUploadProgress(data);
        });

        this.socketio.on('file_transcription_progress', (data) => {
            this.app.handleFileTranscriptionProgress(data);
        });

        this.socketio.on('file_transcription_completed', (data) => {
            this.app.handleFileTranscriptionCompleted(data);
        });

        this.socketio.on('file_upload_error', (data) => {
            console.error('File upload error:', data);
        });

        this.socketio.on('file_transcription_error', (data) => {
            console.error('File transcription error:', data);
            this.app.handleFileTranscriptionError(data);
        });

        this.socketio.on('assemblyai_error', (data) => {
            console.error('AssemblyAI error:', data.error);
            this.app.showToast(`AssemblyAI error: ${data.error}`, 'error');
            this.fallbackToWebSpeech();
        });

        this.socketio.on('assemblyai_disconnected', (data) => {
            this.isConnected = false;
            this.app.showToast('AssemblyAI disconnected', 'warning');
        });
    }

    async waitForConnection(timeout = 5000) {
        return new Promise((resolve, reject) => {
            if (this.isConnected) {
                resolve();
                return;
            }

            const startTime = Date.now();
            const checkConnection = () => {
                if (this.isConnected) {
                    resolve();
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error('Connection timeout'));
                } else {
                    setTimeout(checkConnection, 100);
                }
            };
            checkConnection();
        });
    }

    async validateApiKey() {
        const response = await fetch('/api/assemblyai/validate', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.app.sessionToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `Failed to validate API key: ${response.status}`);
        }

        return await response.json();
    }

    async startRecording() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.sampleRate = this.audioContext.sampleRate;

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            await this.audioContext.audioWorklet.addModule(this.createAudioWorkletProcessor());
            this.processor = new AudioWorkletNode(this.audioContext, 'audio-processor');

            this.processor.port.onmessage = (event) => {
                if (event.data.type === 'audioData' && this.isConnected && this.socketio) {
                    const audioArray = new Uint8Array(event.data.data);
                    const base64Audio = btoa(String.fromCharCode.apply(null, audioArray));

                    this.socketio.emit('send_audio_data', {
                        audio_data: base64Audio
                    });
                }
            };

            this.processor.port.postMessage({
                type: 'setSampleRate',
                sampleRate: this.audioContext.sampleRate
            });

            await this.connect();
            await this.waitForConnection();

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

        } catch (error) {
            console.error('Failed to start AssemblyAI recording:', error);
            this.app.showToast('Failed to start AssemblyAI recording', 'error');
            this.fallbackToWebSpeech();
        }
    }

    createAudioWorkletProcessor() {
        const processorCode = `
            class AudioProcessor extends AudioWorkletProcessor {
                constructor() {
                    super();
                    this.bufferSize = 0;
                    this.buffer = [];
                    this.targetBufferDuration = 100;
                    this.sampleRate = 48000;
                    this.samplesPerBuffer = Math.floor(this.sampleRate * this.targetBufferDuration / 1000);

                    this.port.onmessage = (event) => {
                        if (event.data.type === 'setSampleRate') {
                            this.sampleRate = event.data.sampleRate;
                            this.samplesPerBuffer = Math.floor(this.sampleRate * this.targetBufferDuration / 1000);
                        }
                    };
                }

                process(inputs, outputs, parameters) {
                    const input = inputs[0];
                    if (input.length > 0) {
                        const audioData = input[0];

                        for (let i = 0; i < audioData.length; i++) {
                            this.buffer.push(audioData[i]);
                        }

                        if (this.buffer.length >= this.samplesPerBuffer) {
                            const targetSampleRate = 16000;
                            let processedBuffer = this.buffer;

                            if (this.sampleRate !== targetSampleRate) {
                                const downsampleRatio = this.sampleRate / targetSampleRate;
                                const downsampledLength = Math.floor(this.buffer.length / downsampleRatio);
                                processedBuffer = new Array(downsampledLength);

                                for (let i = 0; i < downsampledLength; i++) {
                                    const sourceIndex = Math.floor(i * downsampleRatio);
                                    processedBuffer[i] = this.buffer[sourceIndex];
                                }
                            }

                            const int16Array = new Int16Array(processedBuffer.length);
                            for (let i = 0; i < processedBuffer.length; i++) {
                                // Improved scaling: clamp input first, then scale
                                const sample = Math.max(-1, Math.min(1, processedBuffer[i]));
                                int16Array[i] = Math.round(sample * 32767);
                            }

                            this.port.postMessage({
                                type: 'audioData',
                                data: int16Array.buffer,
                                duration: (processedBuffer.length / targetSampleRate) * 1000,
                                originalSampleRate: this.sampleRate,
                                targetSampleRate: targetSampleRate
                            });

                            this.buffer = [];
                        }
                    }
                    return true;
                }
            }
            registerProcessor('audio-processor', AudioProcessor);
        `;

        const blob = new Blob([processorCode], { type: 'application/javascript' });
        return URL.createObjectURL(blob);
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

        if (this.socketio && this.isConnected) {
            this.socketio.emit('stop_assemblyai_stream');
        }

        this.isConnected = false;
    }

    fallbackToWebSpeech() {
        this.app.activeTranscriptionService = 'webspeech';
        this.app.showToast('Switched to Web Speech API', 'warning');
        this.app.updateServiceStatus();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AssemblyAIService;
} else if (typeof window !== 'undefined') {
    window.AssemblyAIService = AssemblyAIService;
}