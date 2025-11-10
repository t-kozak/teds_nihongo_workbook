/**
 * Wordbank Flashcards JavaScript
 * Handles flashcard flip interactions
 */

(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const flashcards = document.querySelectorAll('.flashcard');

        flashcards.forEach(function(card) {
            // Handle custom audio play button
            const audioBtn = card.querySelector('.flashcard-audio-btn');
            const audio = card.querySelector('.flashcard-audio');

            if (audioBtn && audio) {
                audioBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    audio.currentTime = 0; // Reset to beginning
                    audio.play();
                });
            }

            card.addEventListener('click', function() {
                const front = this.querySelector('.flashcard-front');
                const back = this.querySelector('.flashcard-back');

                if (front.style.display === 'none') {
                    // Currently showing back, flip to front
                    front.style.display = 'flex';
                    back.style.display = 'none';
                } else {
                    // Currently showing front, flip to back
                    // First, reset all other cards to front
                    flashcards.forEach(function(otherCard) {
                        if (otherCard !== card) {
                            const otherFront = otherCard.querySelector('.flashcard-front');
                            const otherBack = otherCard.querySelector('.flashcard-back');
                            otherFront.style.display = 'flex';
                            otherBack.style.display = 'none';
                        }
                    });

                    // Now flip this card to back
                    front.style.display = 'none';
                    back.style.display = 'flex';
                }
            });
        });
    });
})();
