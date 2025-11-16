/**
 * Main JavaScript Entry Point
 * Imports and initializes all modules
 */

import { initFuriganaToggle } from './modules/furigana-toggle.js';
import { initFlashcards } from './modules/flashcards.js';
import { initFlashcardQuiz } from './modules/flashcard-quiz.js';
import { initWordSpanTooltips } from './modules/wordspan.js';
import { initRealtimeCall, makeCall, endCall, clearStoredApiKey } from './modules/realtime-call.js';

// Initialize all features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initFuriganaToggle();
    initFlashcards();
    initFlashcardQuiz();
    initWordSpanTooltips();
    initRealtimeCall();
});

// Export realtime call functions for global access
window.makeCall = makeCall;
window.endCall = endCall;
window.clearStoredApiKey = clearStoredApiKey;
