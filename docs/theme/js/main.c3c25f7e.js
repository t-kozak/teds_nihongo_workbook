/**
 * Main JavaScript Entry Point
 * Imports and initializes all modules
 */

import { initFuriganaToggle } from './modules/furigana-toggle.6fde0d30.js';
import { initFlashcards } from './modules/flashcards.16d3ee97.js';
import { initFlashcardQuiz } from './modules/flashcard-quiz.a1833b8d.js';
import { initWordSpanTooltips } from './modules/wordspan.550a9bd6.js';

// Initialize all features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initFuriganaToggle();
    initFlashcards();
    initFlashcardQuiz();
    initWordSpanTooltips();
});
