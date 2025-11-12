/**
 * Main JavaScript Entry Point
 * Imports and initializes all modules
 */

import { initFuriganaToggle } from './modules/furigana-toggle.js';
import { initFlashcards } from './modules/flashcards.js';

// Initialize all features when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initFuriganaToggle();
    initFlashcards();
});
