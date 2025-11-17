/**
 * Dialogue Practice Module
 *
 * Manages interactive AI conversation practice buttons
 */

import { makeCall, endCall } from './realtime-call.aba96ec4.js';

/**
 * Initialize all dialogue practice buttons on the page
 */
export function initDialoguePractice() {
    const buttons = document.querySelectorAll('.dialogue-practice-button');

    if (buttons.length === 0) {
        console.log('[DialoguePractice] No dialogue practice buttons found');
        return;
    }

    console.log(`[DialoguePractice] Initializing ${buttons.length} dialogue practice button(s)`);

    buttons.forEach(button => {
        button.addEventListener('click', () => handleDialogueClick(button));
    });
}

/**
 * Handle click on a dialogue practice button
 * @param {HTMLButtonElement} button - The clicked button
 */
async function handleDialogueClick(button) {
    const state = button.dataset.state;

    console.log(`[DialoguePractice] Button clicked, current state: ${state}`);

    if (state === 'connected') {
        // End the active call
        console.log('[DialoguePractice] Ending active call');
        try {
            await endCall();
            updateButtonState(button, 'idle', 'Start Practice');
            clearFeedback(button);
        } catch (error) {
            console.error('[DialoguePractice] Error ending call:', error);
            showError(button, 'Failed to end call. Please refresh the page.');
        }
    } else if (state === 'idle') {
        // Start a new call
        console.log('[DialoguePractice] Starting new call');

        // Get instructions from the JSON script tag
        const instructionsId = button.dataset.instructionsId;
        const scriptTag = document.getElementById(instructionsId);

        if (!scriptTag) {
            console.error(`[DialoguePractice] Instructions script tag not found: ${instructionsId}`);
            showError(button, 'Configuration error. Please refresh the page.');
            return;
        }

        let data;
        try {
            data = JSON.parse(scriptTag.textContent);
        } catch (error) {
            console.error('[DialoguePractice] Error parsing instructions JSON:', error);
            showError(button, 'Configuration error. Please refresh the page.');
            return;
        }

        if (!data.instructions) {
            console.error('[DialoguePractice] No instructions found in data');
            showError(button, 'No instructions provided for this dialogue.');
            return;
        }

        console.log('[DialoguePractice] Instructions loaded, starting call');

        try {
            // Update button to connecting state
            updateButtonState(button, 'connecting', 'Connecting...');
            clearFeedback(button);

            // Start the call (makeCall will handle button state updates)
            await makeCall(data.instructions, 'alloy', {}, button);

            // Update button to connected state
            updateButtonState(button, 'connected', 'End Call');
            console.log('[DialoguePractice] Call started successfully');
        } catch (error) {
            console.error('[DialoguePractice] Error starting call:', error);

            // Show error message to user
            let errorMessage = 'Failed to start call.';
            if (error.message.includes('Microphone')) {
                errorMessage = 'Microphone access denied. Please allow microphone access and try again.';
            } else if (error.message.includes('API key')) {
                errorMessage = 'Invalid API key. Please check your API key and try again.';
            } else if (error.message.includes('cancelled')) {
                errorMessage = 'Call cancelled.';
            } else {
                errorMessage = `Failed to start call: ${error.message}`;
            }

            showError(button, errorMessage);
            updateButtonState(button, 'idle', 'Start Practice');
        }
    } else if (state === 'connecting') {
        // Do nothing while connecting
        console.log('[DialoguePractice] Button clicked while connecting, ignoring');
    }
}

/**
 * Update button state and text
 * @param {HTMLButtonElement} button - The button to update
 * @param {string} state - New state (idle, connecting, connected, error)
 * @param {string} text - New button text
 */
function updateButtonState(button, state, text) {
    console.log(`[DialoguePractice] Updating button state: ${state}, text: ${text}`);
    button.dataset.state = state;
    button.textContent = text;
    button.disabled = (state === 'connecting');
}

/**
 * Show error message in the feedback div
 * @param {HTMLButtonElement} button - The button associated with this dialogue
 * @param {string} message - Error message to display
 */
function showError(button, message) {
    const section = button.closest('.dialogue-practice-section');
    const feedback = section.querySelector('.dialogue-practice-feedback');

    if (!feedback) {
        console.error('[DialoguePractice] Feedback div not found');
        return;
    }

    feedback.textContent = message;
    feedback.classList.add('error');
    feedback.style.display = 'block';

    // Auto-hide after 8 seconds
    setTimeout(() => {
        feedback.style.display = 'none';
        feedback.classList.remove('error');
    }, 8000);
}

/**
 * Clear any feedback messages
 * @param {HTMLButtonElement} button - The button associated with this dialogue
 */
function clearFeedback(button) {
    const section = button.closest('.dialogue-practice-section');
    const feedback = section.querySelector('.dialogue-practice-feedback');

    if (feedback) {
        feedback.style.display = 'none';
        feedback.textContent = '';
        feedback.classList.remove('error');
    }
}
