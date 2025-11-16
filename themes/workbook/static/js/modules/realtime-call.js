/**
 * OpenAI Realtime API Module
 * Handles WebRTC-based real-time audio calls with OpenAI
 */

const API_KEY_STORAGE_KEY = 'openai_realtime_api_key';

/**
 * API Key Management Functions
 */

/**
 * Gets the API key from localStorage
 */
function getStoredApiKey() {
    return localStorage.getItem(API_KEY_STORAGE_KEY);
}

/**
 * Stores the API key in localStorage
 */
function storeApiKey(apiKey) {
    localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
}

/**
 * Removes the API key from localStorage
 */
function clearApiKey() {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
}

/**
 * Creates and shows a popup to prompt for API key
 * @returns {Promise<string>} The API key entered by the user
 */
function promptForApiKey() {
    return new Promise((resolve, reject) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        // Create popup
        const popup = document.createElement('div');
        popup.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            width: 90%;
        `;

        popup.innerHTML = `
            <h2 style="margin-top: 0; margin-bottom: 1rem; color: #333;">OpenAI API Key Required</h2>
            <p style="margin-bottom: 1rem; color: #666;">
                Please enter your OpenAI API key to use the realtime conversation feature.
                Your key will be stored securely in your browser's local storage.
            </p>
            <input
                type="password"
                id="api-key-input"
                placeholder="sk-..."
                style="
                    width: 100%;
                    padding: 0.5rem;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 1rem;
                    margin-bottom: 1rem;
                    box-sizing: border-box;
                "
            />
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button
                    id="api-key-cancel"
                    style="
                        padding: 0.5rem 1rem;
                        border: 1px solid #ddd;
                        background: white;
                        border-radius: 4px;
                        cursor: pointer;
                    "
                >Cancel</button>
                <button
                    id="api-key-submit"
                    style="
                        padding: 0.5rem 1rem;
                        border: none;
                        background: #007bff;
                        color: white;
                        border-radius: 4px;
                        cursor: pointer;
                    "
                >Save & Continue</button>
            </div>
        `;

        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        const input = popup.querySelector('#api-key-input');
        const submitBtn = popup.querySelector('#api-key-submit');
        const cancelBtn = popup.querySelector('#api-key-cancel');

        // Focus input
        setTimeout(() => input.focus(), 100);

        // Handle submit
        const handleSubmit = () => {
            const apiKey = input.value.trim();
            if (!apiKey) {
                alert('Please enter a valid API key');
                return;
            }
            if (!apiKey.startsWith('sk-')) {
                alert('OpenAI API keys should start with "sk-"');
                return;
            }
            document.body.removeChild(overlay);
            storeApiKey(apiKey);
            resolve(apiKey);
        };

        // Handle cancel
        const handleCancel = () => {
            document.body.removeChild(overlay);
            reject(new Error('API key input cancelled'));
        };

        submitBtn.addEventListener('click', handleSubmit);
        cancelBtn.addEventListener('click', handleCancel);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSubmit();
            }
        });
    });
}

/**
 * Gets the API key, prompting the user if not stored
 * @returns {Promise<string>} The API key
 */
async function ensureApiKey() {
    let apiKey = getStoredApiKey();
    if (!apiKey) {
        apiKey = await promptForApiKey();
    }
    return apiKey;
}

class RealtimeCall {
    constructor() {
        this.peerConnection = null;
        this.dataChannel = null;
        this.audioElement = null;
        this.isCallActive = false;
    }

    /**
     * Creates an ephemeral token for the realtime session
     * Note: In production, this should be called from your backend
     * @param {string} voice - The voice to use for the session (e.g., 'alloy', 'marin')
     */
    async createEphemeralToken(voice = 'alloy') {
        try {
            console.log('[RealtimeCall] Getting API key...');
            const apiKey = await ensureApiKey();
            console.log('[RealtimeCall] API key obtained, creating session...');

            const sessionConfig = {
                model: 'gpt-4o-realtime-preview-2024-12-17',
                voice: voice
            };

            console.log('[RealtimeCall] Session config:', sessionConfig);

            const response = await fetch('https://api.openai.com/v1/realtime/sessions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(sessionConfig),
            });

            console.log('[RealtimeCall] Session API response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[RealtimeCall] Session creation failed:', response.status, errorText);
                throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('[RealtimeCall] Session created successfully:', data);
            return data.client_secret.value;
        } catch (error) {
            console.error('[RealtimeCall] Error creating ephemeral token:', error);
            throw error;
        }
    }

    /**
     * Establishes WebRTC connection to OpenAI Realtime API
     */
    async setupWebRTC(ephemeralToken) {
        console.log('[RealtimeCall] Setting up WebRTC connection...');

        // Create peer connection
        this.peerConnection = new RTCPeerConnection();
        console.log('[RealtimeCall] Peer connection created');

        // Add connection state listeners
        this.peerConnection.onconnectionstatechange = () => {
            console.log('[RealtimeCall] Connection state:', this.peerConnection.connectionState);
        };

        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('[RealtimeCall] ICE connection state:', this.peerConnection.iceConnectionState);
        };

        // Set up audio element to play remote audio
        this.audioElement = document.createElement('audio');
        this.audioElement.autoplay = true;
        this.peerConnection.ontrack = (event) => {
            console.log('[RealtimeCall] Received remote track:', event.track.kind);
            this.audioElement.srcObject = event.streams[0];
        };

        // Add local audio track (microphone)
        try {
            console.log('[RealtimeCall] Requesting microphone access...');
            const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('[RealtimeCall] Microphone access granted');
            mediaStream.getTracks().forEach(track => {
                console.log('[RealtimeCall] Adding track:', track.kind);
                this.peerConnection.addTrack(track, mediaStream);
            });
        } catch (error) {
            console.error('[RealtimeCall] Error accessing microphone:', error);
            throw new Error('Microphone access denied');
        }

        // Set up data channel for sending/receiving events
        console.log('[RealtimeCall] Creating data channel...');
        this.dataChannel = this.peerConnection.createDataChannel('oai-events');

        // Create a promise that resolves when the data channel opens
        const dataChannelReady = new Promise((resolve, reject) => {
            this.dataChannel.onopen = () => {
                console.log('[RealtimeCall] ✅ Data channel opened');
                this.isCallActive = true;
                resolve();
            };

            this.dataChannel.onerror = (error) => {
                console.error('[RealtimeCall] Data channel error:', error);
                reject(error);
            };

            // Timeout after 10 seconds
            setTimeout(() => {
                if (this.dataChannel.readyState !== 'open') {
                    reject(new Error('Data channel failed to open within 10 seconds'));
                }
            }, 10000);
        });

        this.dataChannel.onmessage = (event) => {
            console.log('[RealtimeCall] Data channel message received');
            this.handleServerEvent(JSON.parse(event.data));
        };

        this.dataChannel.onclose = () => {
            console.log('[RealtimeCall] Data channel closed');
            this.isCallActive = false;
        };

        // Create and set local description
        console.log('[RealtimeCall] Creating offer...');
        const offer = await this.peerConnection.createOffer();
        await this.peerConnection.setLocalDescription(offer);
        console.log('[RealtimeCall] Local description set');

        // Send offer to OpenAI and get answer
        console.log('[RealtimeCall] Sending offer to OpenAI...');
        const response = await fetch('https://api.openai.com/v1/realtime', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${ephemeralToken}`,
                'Content-Type': 'application/sdp',
            },
            body: offer.sdp,
        });

        console.log('[RealtimeCall] Realtime API response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[RealtimeCall] WebRTC connection failed:', response.status, errorText);
            throw new Error(`Failed to connect: ${response.status} ${response.statusText}`);
        }

        const answerSdp = await response.text();
        console.log('[RealtimeCall] Received answer SDP, setting remote description...');
        await this.peerConnection.setRemoteDescription({
            type: 'answer',
            sdp: answerSdp,
        });
        console.log('[RealtimeCall] ✅ WebRTC setup complete');

        // Wait for data channel to be ready before returning
        console.log('[RealtimeCall] Waiting for data channel to open...');
        await dataChannelReady;
        console.log('[RealtimeCall] ✅ Data channel ready');
    }

    /**
     * Handles events received from the server
     */
    handleServerEvent(event) {
        console.log('Server event:', event);

        switch (event.type) {
            case 'session.created':
                console.log('Session created:', event.session);
                break;
            case 'conversation.item.created':
                console.log('Conversation item created:', event.item);
                break;
            case 'response.done':
                console.log('Response completed:', event.response);
                break;
            case 'error':
                console.error('Server error:', event.error);
                break;
            default:
                console.log('Unhandled event type:', event.type);
        }
    }

    /**
     * Sends a message to the server via data channel
     */
    sendMessage(message) {
        if (this.dataChannel && this.dataChannel.readyState === 'open') {
            console.log('[RealtimeCall] Sending message:', message.type);
            this.dataChannel.send(JSON.stringify(message));
        } else {
            console.warn('[RealtimeCall] Data channel not ready, state:', this.dataChannel?.readyState);
        }
    }

    /**
     * Updates session configuration (e.g., transcription settings)
     */
    updateSession(options = {}) {
        console.log('[RealtimeCall] Updating session with config:', options);

        this.sendMessage({
            type: 'session.update',
            session: options
        });
    }

    /**
     * Sends instructions as a system message
     * @param {string} instructions - The instructions text to send
     */
    sendSystemInstructions(instructions) {
        console.log('[RealtimeCall] Sending system instructions:', instructions);

        const event = {
            type: 'conversation.item.create',
            item: {
                type: 'message',
                role: 'system',
                content: [
                    {
                        type: 'input_text',
                        text: instructions
                    }
                ]
            }
        };

        this.sendMessage(event);
    }

    /**
     * Ends the call and cleans up resources
     */
    async endCall() {
        if (this.dataChannel) {
            this.dataChannel.close();
        }

        if (this.peerConnection) {
            this.peerConnection.close();
        }

        if (this.audioElement) {
            this.audioElement.srcObject = null;
        }

        this.isCallActive = false;
        console.log('Call ended');
    }

    /**
     * Main function to start a call
     */
    async startCall(sessionOptions = {}) {
        try {
            console.log('[RealtimeCall] ========== Starting call ==========');
            console.log('[RealtimeCall] Session options:', sessionOptions);

            // Step 1: Create ephemeral token with voice configuration
            const voice = sessionOptions.voice || 'alloy';
            const ephemeralToken = await this.createEphemeralToken(voice);
            console.log('[RealtimeCall] ✅ Ephemeral token created');

            // Step 2: Setup WebRTC connection (this waits for data channel to be ready)
            await this.setupWebRTC(ephemeralToken);
            console.log('[RealtimeCall] ✅ WebRTC connection established and data channel ready');

            // Step 3: Send instructions as a system message if provided
            if (sessionOptions.instructions) {
                this.sendSystemInstructions(sessionOptions.instructions);
            }

            // Step 4: Update session with other options (excluding voice and instructions)
            const sessionUpdateOptions = { ...sessionOptions };
            delete sessionUpdateOptions.voice; // Voice already configured in token creation
            delete sessionUpdateOptions.instructions; // Instructions sent as system message

            if (Object.keys(sessionUpdateOptions).length > 0) {
                this.updateSession(sessionUpdateOptions);
            }

            console.log('[RealtimeCall] ========== Call started successfully ==========');
            return true;
        } catch (error) {
            console.error('[RealtimeCall] ❌ Failed to start call:', error);
            await this.endCall();
            throw error;
        }
    }
}

// Create a singleton instance
let realtimeCallInstance = null;

/**
 * Main function to make a call - can be used as a click handler
 * @param {string} instructions - Instructions for the conversation topic (will be prepended with base tutor instructions)
 * @param {string} voice - Optional voice to use (defaults to 'alloy')
 * @param {Object} additionalOptions - Optional additional session configuration
 */
export async function makeCall(instructions, voice = 'alloy', additionalOptions = {}) {
    console.log('[makeCall] Called with instructions:', instructions);
    console.log('[makeCall] Voice:', voice);

    // If there's an active call, end it first
    if (realtimeCallInstance?.isCallActive) {
        console.log('[makeCall] Ending existing call...');
        await realtimeCallInstance.endCall();
    }

    // Create new instance
    console.log('[makeCall] Creating new RealtimeCall instance');
    realtimeCallInstance = new RealtimeCall();

    // Base Japanese tutor instructions
    const baseInstructions = `You are a helpful Japanese language tutor. Speak primarily in Japanese at a conversational pace. Help the user practice everyday dialogues and conversations.

${instructions}`;

    console.log('[makeCall] Full instructions:', baseInstructions);

    // Build session options
    const sessionOptions = {
        instructions: baseInstructions,
        voice: voice,
        input_audio_transcription: {
            model: 'whisper-1'
        },
        ...additionalOptions
    };

    console.log('[makeCall] Session options:', sessionOptions);

    try {
        await realtimeCallInstance.startCall(sessionOptions);
        console.log('[makeCall] ✅ Call established successfully');
        return realtimeCallInstance;
    } catch (error) {
        console.error('[makeCall] ❌ Error:', error);
        alert(`Failed to start call: ${error.message}`);
        throw error;
    }
}

/**
 * Ends the current active call
 */
export async function endCall() {
    if (realtimeCallInstance) {
        await realtimeCallInstance.endCall();
        realtimeCallInstance = null;
    }
}

/**
 * Gets the current call instance
 */
export function getCurrentCall() {
    return realtimeCallInstance;
}

/**
 * Clears the stored API key from localStorage
 * Useful if user wants to change their API key
 */
export function clearStoredApiKey() {
    clearApiKey();
    console.log('API key cleared from storage');
}

/**
 * Initializes the module (for consistency with other modules)
 */
export function initRealtimeCall() {
    console.log('Realtime Call module initialized');
    // Any initialization code can go here
}
