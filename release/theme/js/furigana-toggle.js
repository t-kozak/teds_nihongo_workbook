/**
 * Furigana Toggle Functionality
 *
 * Handles showing/hiding hiragana readings above kanji characters
 * and persists the user's preference in localStorage.
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'furigana-visible';
    const toggle = document.getElementById('furigana-toggle');
    const content = document.getElementById('article-content');

    if (!toggle || !content) {
        // Not on an article page, or elements not found
        return;
    }

    /**
     * Load the saved preference from localStorage
     * @returns {boolean} True if furigana should be visible, false otherwise
     */
    function loadPreference() {
        const saved = localStorage.getItem(STORAGE_KEY);
        // Default to true (visible) if no preference is saved
        return saved === null ? true : saved === 'true';
    }

    /**
     * Save the preference to localStorage
     * @param {boolean} visible - Whether furigana should be visible
     */
    function savePreference(visible) {
        localStorage.setItem(STORAGE_KEY, visible.toString());
    }

    /**
     * Apply the furigana visibility state
     * @param {boolean} visible - Whether furigana should be visible
     */
    function applyFuriganaState(visible) {
        if (visible) {
            content.classList.remove('hide-furigana');
        } else {
            content.classList.add('hide-furigana');
        }
    }

    /**
     * Handle toggle change event
     */
    function handleToggleChange() {
        const visible = toggle.checked;
        applyFuriganaState(visible);
        savePreference(visible);
    }

    // Initialize: Load saved preference and apply it
    const savedPreference = loadPreference();
    toggle.checked = savedPreference;
    applyFuriganaState(savedPreference);

    // Listen for changes
    toggle.addEventListener('change', handleToggleChange);
})();
