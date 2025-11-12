/**
 * Furigana Toggle Functionality
 *
 * Handles showing/hiding hiragana readings above kanji characters
 * and persists the user's preference in localStorage.
 */

const STORAGE_KEY = 'furigana-visible';

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
 * @param {HTMLElement} content - The content element to apply the state to
 */
function applyFuriganaState(visible, content) {
    if (visible) {
        content.classList.remove('hide-furigana');
    } else {
        content.classList.add('hide-furigana');
    }
}

/**
 * Initialize furigana toggle functionality
 */
export function initFuriganaToggle() {
    const toggle = document.getElementById('furigana-toggle');
    const content = document.getElementById('article-content');

    if (!toggle || !content) {
        // Not on an article page, or elements not found
        return;
    }

    /**
     * Handle toggle change event
     */
    function handleToggleChange() {
        const visible = toggle.checked;
        applyFuriganaState(visible, content);
        savePreference(visible);
    }

    // Initialize: Load saved preference and apply it
    const savedPreference = loadPreference();
    toggle.checked = savedPreference;
    applyFuriganaState(savedPreference, content);

    // Listen for changes
    toggle.addEventListener('change', handleToggleChange);
}
