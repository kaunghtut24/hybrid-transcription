// Unified WebSocket Manager for centralized communication with polling fallback
// Provides consistent connection management approach across all features
class UnifiedWebSocketManager {
    constructor(sessionToken) {
        this.sessionToken = sessionToken;
        this.socketio = null;

        // Connection lifecycle states
        this.connectionStates = {
            DISCONNECTED: 'disconnected',
            CONNECTING: 'connecting',
            CONNECTED: 'connected',
            RECONNECTING: 'reconnecting',
            FAILED: 'failed'
        };

        this.currentState = this.connectionStates.DISCONNECTED;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.rooms = new Set();
        this.eventHandlers = new Map();

        // Enhanced room management for room-based communication
        this.roomStates = new Map();
        this.roomEventHandlers = new Map();
        this.roomReconnectionData = new Map();

        this.connectionState = {
            connected: false,
            reconnectAttempts: 0,
            lastConnected: null,
            lastDisconnected: null,
            rooms: new Set(),
            connectionDuration: 0,
            totalReconnects: 0
        };

        // Connection lifecycle callbacks
        this.lifecycleCallbacks = {
            onConnecting: [],
            onConnected: [],
            onDisconnected: [],
            onReconnecting: [],
            onFailed: [],
            onStateChange: []
        };

        // Polling fallback configuration
        this.pollingEnabled = false;
        this.pollingIntervals = new Map();
        this.pollingCallbacks = new Map();
        this.fallbackMode = false;
        this.pollingConfig = {
            fileUploadStatus: {
                interval: 2000,
                maxInterval: 10000,
                backoffFactor: 1.5
            },
            transcriptionStatus: {
                interval: 3000,
                maxInterval: 15000,
                backoffFactor: 1.2
            }
        };

        this.reconnectionTimer = null;
        this.connectionStartTime = null;
        this.connectionHealthy = true;
        this.eventQueue = [];
        this.debugMode = false;
    }

    async connect() {
        if (this.connected && this.socketio && this.currentState === this.connectionStates.CONNECTED) {
            return this.socketio;
        }

        try {
            this.setState(this.connectionStates.CONNECTING);
            this.connectionStartTime = Date.now();

            this.socketio = io({
                timeout: 30000,  // Increased timeout for serverless
                reconnection: false,
                // Force polling transport for Vercel serverless compatibility
                transports: ['polling'],  // Only use polling, no websockets
                upgrade: false,  // Disable upgrades to websockets
                forceNew: true,
                rememberUpgrade: false,
                // Additional serverless optimizations
                autoConnect: true,
                forceBase64: false,
                timestampRequests: true,
                // Longer polling timeouts for serverless environments
                pollingTimeout: 90000,  // 90 seconds
                // Disable compression to reduce processing overhead
                compression: false
            });

            this.setupConnectionEventHandlers();

            return new Promise((resolve, reject) => {
                const connectTimeout = setTimeout(() => {
                    this.setState(this.connectionStates.FAILED);
                    reject(new Error('Connection timeout'));
                }, 30000);  // Increased to 30 seconds for serverless

                this.socketio.once('connect', () => {
                    clearTimeout(connectTimeout);
                    resolve(this.socketio);
                });

                this.socketio.once('connect_error', (error) => {
                    clearTimeout(connectTimeout);
                    this.setState(this.connectionStates.FAILED);
                    reject(error);
                });
            });

        } catch (error) {
            console.error('Failed to connect UnifiedWebSocketManager:', error);
            this.setState(this.connectionStates.FAILED);
            throw error;
        }
    }

    setupConnectionEventHandlers() {
        if (!this.socketio) return;

        this.socketio.on('connect', () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.connectionState.connected = true;
            this.connectionState.lastConnected = new Date();
            this.connectionState.connectionDuration = Date.now() - this.connectionStartTime;

            this.setState(this.connectionStates.CONNECTED);
            console.log(`UnifiedWebSocketManager connected (${this.connectionState.connectionDuration}ms)`);

            if (this.fallbackMode) {
                try {
                    this.transitionFromPollingToWebSocket();
                } catch (e) {
                    console.warn('Failed to transition from polling to WebSocket:', e);
                }
            }

            this.processEventQueue();
            this.rejoinRooms();
            this.emitConnectionStatus({ connected: true });
        });

        this.socketio.on('disconnect', (reason) => {
            this.connected = false;
            this.connectionState.connected = false;
            this.connectionState.lastDisconnected = new Date();

            this.setState(this.connectionStates.DISCONNECTED);
            this.emitConnectionStatus({ connected: false, reason });

            if (reason !== 'io client disconnect') {
                this.attemptReconnection();
            }
        });

        this.socketio.on('connect_error', (error) => {
            console.error('UnifiedWebSocketManager connection error:', error);
            this.setState(this.connectionStates.FAILED);
            this.emitEvent('connection_error', {
                error: error.message,
                willRetry: this.reconnectAttempts < this.maxReconnectAttempts
            });
        });

        this.setupEventForwarding();
        this.startHealthMonitoring();
    }

    setState(newState) {
        const oldState = this.currentState;
        this.currentState = newState;
        this.connectionState.reconnectAttempts = this.reconnectAttempts;
        this.executeLifecycleCallbacks(newState);
        this.emitEvent('state_change', {
            oldState,
            newState,
            timestamp: new Date().toISOString(),
            connectionState: this.getConnectionStatus()
        });
    }

    executeLifecycleCallbacks(state) {
        const callbackMap = {
            [this.connectionStates.CONNECTING]: 'onConnecting',
            [this.connectionStates.CONNECTED]: 'onConnected',
            [this.connectionStates.DISCONNECTED]: 'onDisconnected',
            [this.connectionStates.RECONNECTING]: 'onReconnecting',
            [this.connectionStates.FAILED]: 'onFailed'
        };

        const callbackType = callbackMap[state];
        if (callbackType && this.lifecycleCallbacks[callbackType]) {
            this.lifecycleCallbacks[callbackType].forEach(callback => {
                try {
                    callback(this.getConnectionStatus());
                } catch (error) {
                    console.error(`Error in ${callbackType} callback:`, error);
                }
            });
        }

        this.lifecycleCallbacks.onStateChange.forEach(callback => {
            try {
                callback(state, this.getConnectionStatus());
            } catch (error) {
                console.error('Error in onStateChange callback:', error);
            }
        });
    }

    getConnectionStatus() {
        return {
            connected: this.connected,
            state: this.currentState,
            reconnectAttempts: this.reconnectAttempts,
            fallbackMode: this.fallbackMode,
            rooms: Array.from(this.rooms),
            connectionDuration: this.connectionState.connectionDuration,
            totalReconnects: this.connectionState.totalReconnects
        };
    }

    // Event handling methods
    on(event, callback) {
        if (!event || typeof callback !== 'function') {
            console.error('Invalid event registration: event name and callback required');
            return () => {};
        }

        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }

        this.eventHandlers.get(event).push(callback);

        if (this.socketio && !this.socketio.hasListeners(event)) {
            this.socketio.on(event, (data) => {
                this.emitEvent(event, data);
            });
        }

        return () => this.off(event, callback);
    }

    off(event, callback) {
        if (!event) return;

        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            if (callback) {
                const index = handlers.indexOf(callback);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
            } else {
                handlers.length = 0;
            }

            if (handlers.length === 0) {
                this.eventHandlers.delete(event);
            }
        }

        if (this.socketio && (!this.eventHandlers.has(event) || this.eventHandlers.get(event).length === 0)) {
            this.socketio.off(event);
        }
    }

    emit(event, data = {}) {
        if (!event) {
            console.error('Cannot emit: event name is required');
            return false;
        }

        const eventData = {
            sessionToken: this.sessionToken,
            timestamp: Date.now(),
            eventId: this.generateEventId(),
            ...data
        };

        if (!this.connected || !this.socketio) {
            console.warn(`Cannot emit ${event}: not connected, queueing event`);
            this.queueEvent(event, eventData);
            return false;
        }

        try {
            this.socketio.emit(event, eventData);
            return true;
        } catch (error) {
            console.error(`Failed to emit event ${event}:`, error);
            this.emitEvent('emit_error', { event, error: error.message });
            return false;
        }
    }

    emitEvent(event, data = {}) {
        if (!this.eventHandlers.has(event)) return;

        const handlers = this.eventHandlers.get(event);
        const eventData = {
            ...data,
            timestamp: Date.now(),
            eventId: this.generateEventId()
        };

        handlers.forEach((callback, index) => {
            try {
                callback(eventData);
            } catch (error) {
                console.error(`Error in event handler ${index} for ${event}:`, error);
            }
        });
    }

    generateEventId() {
        return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    // Simplified methods for core functionality
    queueEvent(event, data) {
        this.eventQueue.push({ event, data, timestamp: Date.now() });
    }

    processEventQueue() {
        if (this.eventQueue.length === 0) return;
        const events = [...this.eventQueue];
        this.eventQueue = [];
        events.forEach(queuedEvent => {
            try {
                this.emit(queuedEvent.event, queuedEvent.data);
            } catch (error) {
                console.error(`Error processing queued event ${queuedEvent.event}:`, error);
            }
        });
    }

    rejoinRooms() {
        this.rooms.forEach(room => {
            try {
                this.socketio.emit('join_room', {
                    room,
                    sessionToken: this.sessionToken,
                    _rejoin: true
                });
            } catch (error) {
                console.error(`Failed to rejoin room ${room}:`, error);
            }
        });
    }

    attemptReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.setState(this.connectionStates.FAILED);
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
        
        this.setState(this.connectionStates.RECONNECTING);
        
        this.reconnectionTimer = setTimeout(async () => {
            try {
                await this.connect();
                this.reconnectAttempts = 0;
            } catch (error) {
                console.error(`Reconnection attempt ${this.reconnectAttempts} failed:`, error);
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.attemptReconnection();
                } else {
                    this.setState(this.connectionStates.FAILED);
                }
            }
        }, delay);
    }

    disconnect() {
        if (this.reconnectionTimer) {
            clearTimeout(this.reconnectionTimer);
            this.reconnectionTimer = null;
        }

        if (this.socketio) {
            this.socketio.disconnect();
            this.socketio = null;
        }

        this.connected = false;
        this.setState(this.connectionStates.DISCONNECTED);
        this.rooms.clear();
        this.connectionState.rooms.clear();
    }

    // Stub methods for compatibility
    setupEventForwarding() {}
    startHealthMonitoring() {}
    emitConnectionStatus() {}
    transitionFromPollingToWebSocket() {}
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedWebSocketManager;
} else if (typeof window !== 'undefined') {
    window.UnifiedWebSocketManager = UnifiedWebSocketManager;
}