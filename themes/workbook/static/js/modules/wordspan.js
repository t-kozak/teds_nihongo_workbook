/**
 * Japanese Word Tooltip Module
 *
 * Displays English translations in a tooltip when hovering over Japanese words
 * that have been wrapped in <span class="jp-word" data-en-translation="...">
 */

/**
 * Create and return a singleton tooltip element
 * @returns {HTMLElement} The tooltip element
 */
function createTooltip() {
    let tooltip = document.getElementById('jp-word-tooltip');

    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'jp-word-tooltip';
        tooltip.className = 'jp-word-tooltip';
        tooltip.setAttribute('role', 'tooltip');
        document.body.appendChild(tooltip);
    }

    return tooltip;
}

/**
 * Position the tooltip near the target element
 * @param {HTMLElement} tooltip - The tooltip element
 * @param {HTMLElement} target - The target element being hovered
 */
function positionTooltip(tooltip, target) {
    const rect = target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    // Calculate position: center horizontally above the word
    let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
    let top = rect.top - tooltipRect.height - 8; // 8px gap above the word

    // Ensure tooltip doesn't go off the left edge
    if (left < 10) {
        left = 10;
    }

    // Ensure tooltip doesn't go off the right edge
    const maxLeft = window.innerWidth - tooltipRect.width - 10;
    if (left > maxLeft) {
        left = maxLeft;
    }

    // If tooltip would go above viewport, show it below instead
    if (top < 10) {
        top = rect.bottom + 8;
        tooltip.classList.add('below');
    } else {
        tooltip.classList.remove('below');
    }

    tooltip.style.left = `${left + window.scrollX}px`;
    tooltip.style.top = `${top + window.scrollY}px`;
}

/**
 * Show the tooltip for a given element
 * @param {HTMLElement} target - The element to show tooltip for
 * @param {HTMLElement} tooltip - The tooltip element
 */
function showTooltip(target, tooltip) {
    const translation = target.getAttribute('data-en-translation');

    if (!translation) {
        return;
    }

    // Parse pipe-separated translations
    const translations = translation
        .split('|')
        .map(t => t.trim())
        .filter(t => t.length > 0);

    if (translations.length === 0) {
        return;
    }

    // Build tooltip content
    if (translations.length === 1) {
        tooltip.textContent = translations[0];
    } else {
        // Multiple translations: show as a list
        tooltip.innerHTML = translations
            .map(t => `<div class="translation-item">${escapeHtml(t)}</div>`)
            .join('');
    }

    // Show tooltip
    tooltip.classList.add('visible');

    // Position after content is set (so we have correct dimensions)
    requestAnimationFrame(() => {
        positionTooltip(tooltip, target);
    });
}

/**
 * Hide the tooltip
 * @param {HTMLElement} tooltip - The tooltip element
 */
function hideTooltip(tooltip) {
    tooltip.classList.remove('visible');
}

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize tooltip functionality for all jp-word elements
 */
export function initWordSpanTooltips() {
    const tooltip = createTooltip();
    let currentTarget = null;
    let commandKeyPressed = false;

    /**
     * Handle keyboard events for Command/Ctrl key press/hold
     */
    function handleKeyDown(event) {
        // Check for Command key (metaKey on Mac) or Ctrl key on other platforms
        if ((event.metaKey || event.ctrlKey) && !commandKeyPressed) {
            commandKeyPressed = true;
        }
    }

    function handleKeyUp(event) {
        // Check if Command/Ctrl key was released
        if (!event.metaKey && !event.ctrlKey && commandKeyPressed) {
            commandKeyPressed = false;
            // Hide tooltip when key is released
            if (currentTarget) {
                hideTooltip(tooltip);
                currentTarget.classList.remove('jp-word-active');
                currentTarget = null;
            }
        }
    }

    /**
     * Handle window blur to reset command key state
     */
    function handleBlur() {
        if (commandKeyPressed) {
            commandKeyPressed = false;
            if (currentTarget) {
                hideTooltip(tooltip);
                currentTarget.classList.remove('jp-word-active');
                currentTarget = null;
            }
        }
    }

    // Use event delegation for better performance
    document.addEventListener('mouseover', (event) => {
        // Only show tooltip if Command/Ctrl key is pressed
        if (!commandKeyPressed) {
            return;
        }

        const target = event.target.closest('.jp-word');

        if (target && target.hasAttribute('data-en-translation')) {
            currentTarget = target;
            target.classList.add('jp-word-active');
            console.log('Added jp-word-active class to:', target, 'Classes:', target.className);
            showTooltip(target, tooltip);
        }
    });

    document.addEventListener('mouseout', (event) => {
        const target = event.target.closest('.jp-word');

        if (target && target === currentTarget) {
            hideTooltip(tooltip);
            target.classList.remove('jp-word-active');
            currentTarget = null;
        }
    });

    // Listen for Command/Ctrl key press and hold
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);

    // Hide tooltip on scroll
    document.addEventListener('scroll', () => {
        if (currentTarget && commandKeyPressed) {
            // Update position while scrolling instead of hiding
            requestAnimationFrame(() => {
                positionTooltip(tooltip, currentTarget);
            });
        }
    });

    // Hide tooltip on window resize
    window.addEventListener('resize', () => {
        if (currentTarget && commandKeyPressed) {
            positionTooltip(tooltip, currentTarget);
        }
    });
}
