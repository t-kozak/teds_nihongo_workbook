/**
 * Main JavaScript Entry Point
 * Imports and initializes all modules
 */

import { initFuriganaToggle } from './modules/furigana-toggle.6fde0d30.js';
import { initFlashcards } from './modules/flashcards.16d3ee97.js';
import { initFlashcardQuiz } from './modules/flashcard-quiz.4ace5b14.js';
import { initWordSpanTooltips } from './modules/wordspan.550a9bd6.js';
import { initRealtimeCall, makeCall, endCall, clearStoredApiKey } from './modules/realtime-call.aba96ec4.js';
import { initDialoguePractice } from './modules/dialogue-practice.4d29730f.js';

// Initialize all features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initFuriganaToggle();
    initFlashcards();
    initFlashcardQuiz();
    initWordSpanTooltips();
    initRealtimeCall();
    initDialoguePractice();
});

// Export realtime call functions for global access
window.makeCall = makeCall;
window.endCall = endCall;
window.clearStoredApiKey = clearStoredApiKey;
