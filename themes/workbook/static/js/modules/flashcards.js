/**
 * Wordbank Flashcards JavaScript
 * Handles flashcard flip interactions
 */

/**
 * Reset all flashcards to show the front
 * @param {NodeList} flashcards - All flashcard elements
 * @param {HTMLElement} exceptCard - Card to exclude from reset
 */
function resetOtherCards(flashcards, exceptCard) {
    flashcards.forEach(function(otherCard) {
        if (otherCard !== exceptCard) {
            const otherFront = otherCard.querySelector('.flashcard-front');
            const otherBack = otherCard.querySelector('.flashcard-back');
            otherFront.style.display = 'flex';
            otherBack.style.display = 'none';
        }
    });
}

/**
 * Handle flashcard flip
 * @param {HTMLElement} card - The flashcard element
 * @param {NodeList} allCards - All flashcard elements
 */
function handleCardFlip(card, allCards) {
    const front = card.querySelector('.flashcard-front');
    const back = card.querySelector('.flashcard-back');

    if (front.style.display === 'none') {
        // Currently showing back, flip to front
        front.style.display = 'flex';
        back.style.display = 'none';
    } else {
        // Currently showing front, flip to back
        // First, reset all other cards to front
        resetOtherCards(allCards, card);

        // Now flip this card to back
        front.style.display = 'none';
        back.style.display = 'flex';
    }
}

/**
 * Handle audio button click
 * @param {Event} e - Click event
 * @param {HTMLAudioElement} audio - Audio element to play
 */
function handleAudioClick(e, audio) {
    e.stopPropagation();
    audio.currentTime = 0; // Reset to beginning
    audio.play();
}

/**
 * Initialize flashcard functionality
 */
export function initFlashcards() {
    const flashcards = document.querySelectorAll('.flashcard');

    if (flashcards.length === 0) {
        // No flashcards on this page
        return;
    }

    flashcards.forEach(function(card) {
        // Handle custom audio play button
        const audioBtn = card.querySelector('.flashcard-audio-btn');
        const audio = card.querySelector('.flashcard-audio');

        if (audioBtn && audio) {
            audioBtn.addEventListener('click', (e) => handleAudioClick(e, audio));
        }

        // Handle card flip
        card.addEventListener('click', () => handleCardFlip(card, flashcards));
    });
}
