/**
 * Wordbank Flashcard Quiz Module
 * Implements interactive quiz mode with progress tracking and local storage persistence
 */

/**
 * Quiz state management
 */
class FlashcardQuiz {
    constructor(quizData) {
        this.allWords = quizData || [];
        this.progress = {}; // { word: correctCount }
        this.threshold = 3; // Number of correct answers to "memorize" a word
        this.batchSize = 10; // Number of words per session
        this.currentWord = null;
        this.overlay = null;
        this.currentBatch = []; // Current batch of words being studied
        this.currentBatchIndex = 0; // Which batch we're on
        this.storageKey = `flashcard_quiz_progress_${window.location.pathname}`;

        // Load progress and settings from localStorage
        this.loadProgress();
        this.loadSettings();
    }

    /**
     * Load progress from localStorage
     */
    loadProgress() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                this.progress = JSON.parse(stored);
            }
        } catch (e) {
            console.error('Failed to load quiz progress:', e);
            this.progress = {};
        }
    }

    /**
     * Save progress to localStorage
     */
    saveProgress() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.progress));
        } catch (e) {
            console.error('Failed to save quiz progress:', e);
        }
    }

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        try {
            const stored = localStorage.getItem('flashcard_quiz_settings');
            if (stored) {
                const settings = JSON.parse(stored);
                this.threshold = settings.threshold || 3;
                this.batchSize = settings.batchSize || 10;
            }
        } catch (e) {
            console.error('Failed to load quiz settings:', e);
        }
    }

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        try {
            const settings = {
                threshold: this.threshold,
                batchSize: this.batchSize
            };
            localStorage.setItem('flashcard_quiz_settings', JSON.stringify(settings));
        } catch (e) {
            console.error('Failed to save quiz settings:', e);
        }
    }

    /**
     * Get unmemorized words (sorted by progress for consistency)
     */
    getUnmemorizedWords() {
        const unmemorized = this.allWords.filter(item => {
            const count = this.progress[item.id] || 0;
            return count < this.threshold;
        });

        // Sort by progress count (ascending) for consistent batch ordering
        unmemorized.sort((a, b) => {
            const countA = this.progress[a.id] || 0;
            const countB = this.progress[b.id] || 0;
            return countA - countB;
        });

        return unmemorized;
    }

    /**
     * Get memorized words count
     */
    getMemorizedCount() {
        return this.allWords.filter(item => {
            const count = this.progress[item.id] || 0;
            return count >= this.threshold;
        }).length;
    }

    /**
     * Initialize a new batch
     */
    startNewBatch() {
        const unmemorized = this.getUnmemorizedWords();
        const startIdx = this.currentBatchIndex * this.batchSize;
        this.currentBatch = unmemorized.slice(startIdx, startIdx + this.batchSize);
        return this.currentBatch.length > 0;
    }

    /**
     * Get words in current batch that are not yet memorized
     */
    getCurrentBatchUnmemorized() {
        return this.currentBatch.filter(item => {
            const count = this.progress[item.id] || 0;
            return count < this.threshold;
        });
    }

    /**
     * Check if current batch is complete
     */
    isBatchComplete() {
        return this.getCurrentBatchUnmemorized().length === 0;
    }

    /**
     * Get total number of batches available
     */
    getTotalBatches() {
        const unmemorized = this.getUnmemorizedWords();
        return Math.ceil(unmemorized.length / this.batchSize);
    }

    /**
     * Check if there are more batches available
     */
    hasMoreBatches() {
        return this.currentBatchIndex + 1 < this.getTotalBatches();
    }

    /**
     * Move to next batch
     */
    nextBatch() {
        this.currentBatchIndex++;
        return this.startNewBatch();
    }

    /**
     * Select next word for quiz (weighted by least practiced, from current batch)
     */
    selectNextWord() {
        const batchUnmemorized = this.getCurrentBatchUnmemorized();

        if (batchUnmemorized.length === 0) {
            return null; // Batch complete!
        }

        // Weight by least practiced (lower count = higher probability)
        const weighted = batchUnmemorized.map(item => ({
            item,
            weight: this.threshold - (this.progress[item.id] || 0)
        }));

        // Simple weighted random selection
        const totalWeight = weighted.reduce((sum, entry) => sum + entry.weight, 0);
        let random = Math.random() * totalWeight;

        for (const entry of weighted) {
            random -= entry.weight;
            if (random <= 0) {
                return entry.item;
            }
        }

        // Fallback to first item
        return batchUnmemorized[0];
    }

    /**
     * Record answer
     */
    recordAnswer(itemId, correct) {
        if (correct) {
            this.progress[itemId] = (this.progress[itemId] || 0) + 1;
            this.saveProgress();
        }
        // Don't decrement on wrong answers to avoid frustration
    }

    /**
     * Normalize text for comparison (handles both kanji and hiragana)
     * Strips HTML tags, punctuation, and normalizes whitespace
     */
    normalizeText(text) {
        // Strip HTML tags (from wordspan plugin)
        const withoutHTML = text.replace(/<[^>]*>/g, '');
        // Remove Japanese and common punctuation marks
        // Includes: 。、！？ー（）「」『』【】・：；,. and other common punctuation
        const withoutPunctuation = withoutHTML.replace(/[。、！？ー…・：；～〜（）()「」『』【】［］\[\]｛｝{}、,\.!?:;'"'"\"]/g, '');
        // Remove all whitespace and convert to lowercase
        return withoutPunctuation.trim().toLowerCase().replace(/\s+/g, '');
    }

    /**
     * Check if answer is correct (checks against all possible answers)
     */
    checkAnswer(userInput, possibleAnswers) {
        const normalized = this.normalizeText(userInput);
        // Check if user input matches any of the possible answers
        return possibleAnswers.some(answer => {
            const answerNormalized = this.normalizeText(answer);
            return normalized === answerNormalized;
        });
    }

    /**
     * Reset progress for all words
     */
    resetProgress() {
        this.progress = {};
        this.saveProgress();
    }
}

/**
 * UI Controller for the quiz
 */
class QuizUI {
    constructor(quiz) {
        this.quiz = quiz;
        this.overlay = null;
        this.inputElement = null;
        this.isAnimating = false;
        this.viewportHandler = null;
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * Create and show the quiz overlay
     */
    show() {
        // Load settings before starting
        this.quiz.loadSettings();

        // Initialize first batch
        this.quiz.currentBatchIndex = 0;
        if (!this.quiz.startNewBatch()) {
            // No words to study - show completion immediately
            alert('All words memorized! Great job!');
            return;
        }

        // Create overlay HTML
        const overlay = document.createElement('div');
        overlay.className = 'quiz-overlay';
        overlay.innerHTML = `
            <div class="quiz-container">
                <div class="quiz-header">
                    <div class="quiz-progress">
                        <span class="quiz-progress-text"></span>
                    </div>
                    <button class="quiz-close-btn" type="button" aria-label="Close">&times;</button>
                </div>
                <div class="quiz-content">
                    <div class="quiz-card">
                        <div class="quiz-card-image-container">
                            <img class="quiz-card-image" src="" alt="" loading="lazy">
                            <div class="quiz-card-translation"></div>
                            <div class="quiz-feedback"></div>
                        </div>
                        <div class="quiz-card-input-container">
                            <input type="text" class="quiz-card-input" placeholder="Type the Japanese word..." autocomplete="off" spellcheck="false" lang="ja" inputmode="text">
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.overlay = overlay;
        this.inputElement = overlay.querySelector('.quiz-card-input');

        // Setup event listeners
        this.setupEventListeners();

        // Setup mobile keyboard handling
        if (this.isMobile) {
            this.setupMobileKeyboardHandling();

            // On mobile: hide overlay initially, focus input to trigger keyboard,
            // then show overlay after keyboard is up
            overlay.style.opacity = '0';
            overlay.style.pointerEvents = 'none';

            // Focus input to trigger keyboard
            this.inputElement.focus();

            // Wait for keyboard to appear, then show overlay
            setTimeout(() => {
                overlay.style.opacity = '';
                overlay.style.pointerEvents = '';
            }, 300);
        } else {
            // Desktop: normal flow
            setTimeout(() => this.inputElement.focus(), 100);
        }

        // Show first word
        this.nextWord();
    }

    /**
     * Setup mobile keyboard handling using Visual Viewport API
     */
    setupMobileKeyboardHandling() {
        if (!window.visualViewport) {
            // Fallback for browsers without Visual Viewport API
            return;
        }

        const viewport = window.visualViewport;
        let isFirstResize = true;

        this.viewportHandler = () => {
            // Calculate available height (viewport height minus some padding)
            const availableHeight = viewport.height - 20; // 20px for padding

            // Update CSS variable for available height
            this.overlay.style.setProperty('--available-height', `${availableHeight}px`);

            // Add class to indicate keyboard is active
            // Keyboard is considered active when viewport is significantly smaller than window
            const keyboardActive = viewport.height < window.innerHeight * 0.75;

            if (keyboardActive) {
                this.overlay.classList.add('mobile-keyboard-active');

                // On first keyboard appearance, make overlay visible
                if (isFirstResize && this.overlay.style.opacity === '0') {
                    this.overlay.style.opacity = '';
                    this.overlay.style.pointerEvents = '';
                    isFirstResize = false;
                }
            } else {
                this.overlay.classList.remove('mobile-keyboard-active');
            }
        };

        // Listen to viewport changes
        viewport.addEventListener('resize', this.viewportHandler);
        viewport.addEventListener('scroll', this.viewportHandler);

        // Initial call
        this.viewportHandler();
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Close button
        this.overlay.querySelector('.quiz-close-btn').addEventListener('click', () => {
            this.hide();
        });

        // ESC key to close
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                const settingsPanel = this.overlay.querySelector('.quiz-settings-panel');
                if (!settingsPanel || !settingsPanel.style.display.includes('block')) {
                    this.hide();
                }
            }
        };
        document.addEventListener('keydown', escHandler);
        this.overlay.dataset.escHandler = 'attached';

        // Setup input listeners
        this.setupInputListeners();

        // Click outside to close
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        });
    }

    /**
     * Setup input event listeners (can be called multiple times when restoring quiz card)
     */
    setupInputListeners() {
        // Input submission - detect Enter key in input value
        this.inputElement.addEventListener('input', (e) => {
            const value = this.inputElement.value;

            // Check if Enter was pressed (newline in text)
            if (value.includes('\n')) {
                e.preventDefault();

                // Remove the newline
                const cleanValue = value.replace(/\n/g, '');
                this.inputElement.value = cleanValue;

                if (this.isAnimating) {
                    // If showing feedback, move to next word
                    this.nextWord();
                } else {
                    // Only check answer if input is not empty
                    if (cleanValue.trim().length > 0) {
                        this.checkAnswer();
                    }
                }

                return;
            }
        });

        // Also listen to keydown for Enter key (backup method)
        this.inputElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();

                if (this.isAnimating) {
                    // If showing feedback, move to next word
                    this.nextWord();
                } else {
                    // Only check answer if input is not empty
                    if (this.inputElement.value.trim().length > 0) {
                        this.checkAnswer();
                    }
                }
            }
        });
    }

    /**
     * Hide the overlay
     */
    hide() {
        // Clean up viewport listeners
        if (this.viewportHandler && window.visualViewport) {
            window.visualViewport.removeEventListener('resize', this.viewportHandler);
            window.visualViewport.removeEventListener('scroll', this.viewportHandler);
            this.viewportHandler = null;
        }

        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    }

    /**
     * Update progress display
     */
    updateProgress() {
        const memorizedCount = this.quiz.getMemorizedCount();
        const totalCount = this.quiz.allWords.length;
        const progressText = this.overlay.querySelector('.quiz-progress-text');
        progressText.textContent = `${memorizedCount} / ${totalCount} memorized`;
    }

    /**
     * Restore the quiz card structure (after showing completion screens)
     */
    restoreQuizCard() {
        const content = this.overlay.querySelector('.quiz-content');
        content.innerHTML = `
            <div class="quiz-card">
                <div class="quiz-card-image-container">
                    <img class="quiz-card-image" src="" alt="" loading="lazy">
                    <div class="quiz-card-translation"></div>
                    <div class="quiz-feedback"></div>
                </div>
                <div class="quiz-card-input-container">
                    <input type="text" class="quiz-card-input" placeholder="Type the Japanese word..." autocomplete="off" spellcheck="false" lang="ja" inputmode="text">
                </div>
            </div>
        `;

        // Re-assign input element reference
        this.inputElement = content.querySelector('.quiz-card-input');

        // Re-setup input event listeners
        this.setupInputListeners();
    }

    /**
     * Display next word
     */
    nextWord() {
        const item = this.quiz.selectNextWord();

        if (!item) {
            // Batch complete - check if there are more batches or if all done
            if (this.quiz.hasMoreBatches()) {
                this.showBatchComplete();
            } else {
                this.showCompletion();
            }
            return;
        }

        this.quiz.currentWord = item;
        this.isAnimating = false;

        // Update image
        const img = this.overlay.querySelector('.quiz-card-image');
        img.src = item.question.imageUrl;
        img.alt = item.question.text;

        // Update translation overlay
        const translation = this.overlay.querySelector('.quiz-card-translation');
        translation.textContent = item.question.text;

        // Clear input but keep it focused and enabled
        this.inputElement.value = '';

        // Clear feedback
        const feedback = this.overlay.querySelector('.quiz-feedback');
        feedback.className = 'quiz-feedback';
        feedback.innerHTML = '';

        // Update progress
        this.updateProgress();

        // Always maintain focus to keep keyboard visible
        // Use a small delay to ensure DOM updates complete
        if (document.activeElement !== this.inputElement) {
            setTimeout(() => {
                this.inputElement.focus();
            }, 50);
        }
    }

    /**
     * Check the user's answer
     */
    checkAnswer() {
        if (this.isAnimating || !this.quiz.currentWord) {
            return;
        }

        const userInput = this.inputElement.value;
        const correct = this.quiz.checkAnswer(userInput, this.quiz.currentWord.answers);

        // Record answer
        this.quiz.recordAnswer(this.quiz.currentWord.id, correct);

        // Show feedback
        this.showFeedback(correct);
    }

    /**
     * Show feedback animation
     */
    showFeedback(correct) {
        this.isAnimating = true;

        const feedback = this.overlay.querySelector('.quiz-feedback');
        feedback.innerHTML = ''; // Clear previous content

        if (correct) {
            // Show correct feedback overlay
            feedback.className = 'quiz-feedback correct show';

            const icon = document.createElement('div');
            icon.className = 'quiz-feedback-icon';
            icon.textContent = '✓';
            feedback.appendChild(icon);

            const text = document.createElement('div');
            text.className = 'quiz-feedback-text';
            text.textContent = 'Correct!';
            feedback.appendChild(text);

            // Automatically move to next word after brief delay
            setTimeout(() => {
                this.nextWord();
            }, 1200);
        } else {
            // Show incorrect feedback overlay with correct answers
            feedback.className = 'quiz-feedback incorrect show';

            const icon = document.createElement('div');
            icon.className = 'quiz-feedback-icon';
            icon.textContent = '✗';
            feedback.appendChild(icon);

            const text = document.createElement('div');
            text.className = 'quiz-feedback-text';
            text.textContent = 'Incorrect';
            feedback.appendChild(text);

            const correctAnswer = document.createElement('div');
            correctAnswer.className = 'quiz-correct-answer';
            // Show all possible answers (strip HTML tags for display)
            const answers = this.quiz.currentWord.answers.map(ans => ans.replace(/<[^>]*>/g, ''));
            if (answers.length === 1) {
                correctAnswer.textContent = `Answer: ${answers[0]}`;
            } else {
                correctAnswer.textContent = `Answers: ${answers.join(', ')}`;
            }
            feedback.appendChild(correctAnswer);

            // Show hint to press Enter
            const hint = document.createElement('div');
            hint.style.cssText = 'margin-top: 8px; font-size: 14px; color: rgba(255, 255, 255, 0.9);';
            hint.textContent = 'Press Enter to continue';
            feedback.appendChild(hint);
        }

        // Always keep focus on input to maintain keyboard
        setTimeout(() => {
            this.inputElement.focus();
        }, 100);
    }

    /**
     * Show batch completion screen
     */
    showBatchComplete() {
        const content = this.overlay.querySelector('.quiz-content');
        const batchSize = this.quiz.currentBatch.length;
        const totalUnmemorized = this.quiz.getUnmemorizedWords().length;
        const totalMemorized = this.quiz.getMemorizedCount();
        const totalWords = this.quiz.allWords.length;

        content.innerHTML = `
            <div class="quiz-completion">
                <div class="quiz-completion-icon">✓</div>
                <h2>Batch Complete!</h2>
                <p>You've completed ${batchSize} words. ${totalUnmemorized} more to go!</p>
                <p style="font-size: 16px; color: #718096;">Overall progress: ${totalMemorized} / ${totalWords} memorized</p>
                <div class="quiz-completion-actions">
                    <button class="quiz-next-batch-btn" type="button">Next Batch</button>
                    <button class="quiz-finish-btn" type="button">Finish</button>
                </div>
            </div>
        `;

        // Setup next batch button
        content.querySelector('.quiz-next-batch-btn').addEventListener('click', () => {
            if (this.quiz.nextBatch()) {
                // Restore the quiz card structure before showing next word
                this.restoreQuizCard();
                this.nextWord();
            } else {
                this.showCompletion();
            }
        });

        // Setup finish button
        content.querySelector('.quiz-finish-btn').addEventListener('click', () => {
            this.hide();
        });
    }

    /**
     * Show completion screen (all words memorized)
     */
    showCompletion() {
        const content = this.overlay.querySelector('.quiz-content');
        const totalWords = this.quiz.allWords.length;
        const allMemorized = this.quiz.getMemorizedCount() === totalWords;

        content.innerHTML = `
            <div class="quiz-completion">
                <div class="quiz-completion-icon">🎉</div>
                <h2>Congratulations!</h2>
                <p>${allMemorized ? `You've memorized all ${totalWords} words!` : `Great job on your progress!`}</p>
                <div class="quiz-completion-actions">
                    <button class="quiz-restart-btn" type="button">Reset Progress</button>
                    <button class="quiz-finish-btn" type="button">Close</button>
                </div>
            </div>
        `;

        // Setup restart button
        content.querySelector('.quiz-restart-btn').addEventListener('click', () => {
            if (confirm('Reset all progress and start over?')) {
                this.quiz.resetProgress();
                this.quiz.currentBatchIndex = 0;
                if (this.quiz.startNewBatch()) {
                    // Restore the quiz card structure before showing next word
                    this.restoreQuizCard();
                    this.nextWord();
                } else {
                    this.hide();
                }
            }
        });

        // Setup close button
        content.querySelector('.quiz-finish-btn').addEventListener('click', () => {
            this.hide();
        });
    }
}

/**
 * Standalone Settings Modal
 */
class SettingsModal {
    constructor(quiz) {
        this.quiz = quiz;
        this.modal = null;
    }

    show() {
        // Create modal overlay
        const modal = document.createElement('div');
        modal.className = 'quiz-settings-modal-overlay';
        modal.innerHTML = `
            <div class="quiz-settings-modal-container">
                <div class="quiz-settings-modal-header">
                    <h3>Quiz Settings</h3>
                    <button class="quiz-settings-modal-close" type="button" aria-label="Close">&times;</button>
                </div>
                <div class="quiz-settings-option">
                    <label for="quiz-threshold-modal">Correct answers to memorize:</label>
                    <input type="number" id="quiz-threshold-modal" min="1" max="10" value="${this.quiz.threshold}">
                </div>
                <div class="quiz-settings-option">
                    <label for="quiz-batch-size-modal">Words per session:</label>
                    <input type="number" id="quiz-batch-size-modal" min="5" max="50" step="5" value="${this.quiz.batchSize}">
                </div>
                <div class="quiz-settings-actions">
                    <button class="quiz-reset-btn" type="button">Reset Progress</button>
                    <button class="quiz-settings-close-btn" type="button">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.modal = modal;

        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Close button
        this.modal.querySelector('.quiz-settings-modal-close').addEventListener('click', () => {
            this.hide();
        });

        // Close button (bottom)
        this.modal.querySelector('.quiz-settings-close-btn').addEventListener('click', () => {
            this.hide();
        });

        // Threshold change
        this.modal.querySelector('#quiz-threshold-modal').addEventListener('change', (e) => {
            const newThreshold = parseInt(e.target.value, 10);
            if (newThreshold >= 1 && newThreshold <= 10) {
                this.quiz.threshold = newThreshold;
                this.quiz.saveSettings();
            }
        });

        // Batch size change
        this.modal.querySelector('#quiz-batch-size-modal').addEventListener('change', (e) => {
            const newBatchSize = parseInt(e.target.value, 10);
            if (newBatchSize >= 5 && newBatchSize <= 50) {
                this.quiz.batchSize = newBatchSize;
                this.quiz.saveSettings();
            }
        });

        // Reset progress button
        this.modal.querySelector('.quiz-reset-btn').addEventListener('click', () => {
            if (confirm('Are you sure you want to reset all progress? This cannot be undone.')) {
                this.quiz.resetProgress();
                this.hide();
            }
        });

        // Click outside to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // ESC key to close
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.hide();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    hide() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
    }
}

/**
 * Initialize the flashcard quiz functionality
 */
export function initFlashcardQuiz() {
    const quizButtons = document.querySelectorAll('.quiz-button');

    if (quizButtons.length === 0) {
        // No quiz buttons on this page
        return;
    }

    // Setup each quiz button (there may be multiple quiz sections)
    quizButtons.forEach(button => {
        // Get the quiz data ID from the button's data attribute
        const quizDataId = button.dataset.quizDataId;
        if (!quizDataId) {
            console.error('Quiz button missing data-quiz-data-id attribute');
            return;
        }

        // Find the corresponding quiz data script by ID
        const dataScript = document.getElementById(quizDataId);
        if (!dataScript) {
            console.error(`Quiz data script not found: ${quizDataId}`);
            return;
        }

        let quizData;
        try {
            quizData = JSON.parse(dataScript.textContent);
        } catch (e) {
            console.error('Failed to parse quiz data:', e);
            return;
        }

        // Create quiz instance for this section
        const quiz = new FlashcardQuiz(quizData);
        const ui = new QuizUI(quiz);
        const settingsModal = new SettingsModal(quiz);

        // Handle quiz button click
        button.addEventListener('click', () => {
            ui.show();
        });

        // Find and setup settings button (should be next to quiz button)
        const settingsButton = button.parentElement.querySelector('.quiz-settings-external-btn');
        if (settingsButton) {
            settingsButton.addEventListener('click', () => {
                settingsModal.show();
            });
        }
    });
}
