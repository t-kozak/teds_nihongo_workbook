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
        this.currentWord = null;
        this.overlay = null;
        this.storageKey = `flashcard_quiz_progress_${window.location.pathname}`;

        // Load progress from localStorage
        this.loadProgress();
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
            const settings = { threshold: this.threshold };
            localStorage.setItem('flashcard_quiz_settings', JSON.stringify(settings));
        } catch (e) {
            console.error('Failed to save quiz settings:', e);
        }
    }

    /**
     * Get unmemorized words
     */
    getUnmemorizedWords() {
        return this.allWords.filter(item => {
            const count = this.progress[item.id] || 0;
            return count < this.threshold;
        });
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
     * Select next word for quiz (weighted by least practiced)
     */
    selectNextWord() {
        const unmemorized = this.getUnmemorizedWords();

        if (unmemorized.length === 0) {
            return null; // Quiz complete!
        }

        // Weight by least practiced (lower count = higher probability)
        const weighted = unmemorized.map(item => ({
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
        return unmemorized[0];
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
    }

    /**
     * Create and show the quiz overlay
     */
    show() {
        // Load settings before starting
        this.quiz.loadSettings();

        // Create overlay HTML
        const overlay = document.createElement('div');
        overlay.className = 'quiz-overlay';
        overlay.innerHTML = `
            <div class="quiz-container">
                <div class="quiz-header">
                    <div class="quiz-progress">
                        <span class="quiz-progress-text"></span>
                    </div>
                    <button class="quiz-settings-btn" type="button" aria-label="Settings">⚙️</button>
                    <button class="quiz-close-btn" type="button" aria-label="Close">&times;</button>
                </div>
                <div class="quiz-content">
                    <div class="quiz-card">
                        <div class="quiz-card-image-container">
                            <img class="quiz-card-image" src="" alt="" loading="lazy">
                            <div class="quiz-card-translation"></div>
                        </div>
                        <div class="quiz-card-input-container">
                            <input type="text" class="quiz-card-input" placeholder="Type the Japanese word..." autocomplete="off" spellcheck="false" lang="ja" inputmode="text">
                        </div>
                        <div class="quiz-feedback"></div>
                    </div>
                </div>
                <div class="quiz-settings-panel" style="display: none;">
                    <h3>Quiz Settings</h3>
                    <div class="quiz-settings-option">
                        <label for="quiz-threshold">Correct answers to memorize:</label>
                        <input type="number" id="quiz-threshold" min="1" max="10" value="${this.quiz.threshold}">
                    </div>
                    <div class="quiz-settings-actions">
                        <button class="quiz-reset-btn" type="button">Reset Progress</button>
                        <button class="quiz-settings-close-btn" type="button">Close</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.overlay = overlay;
        this.inputElement = overlay.querySelector('.quiz-card-input');

        // Setup event listeners
        this.setupEventListeners();

        // Focus input
        setTimeout(() => this.inputElement.focus(), 100);

        // Show first word
        this.nextWord();
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
            if (e.key === 'Escape' && !this.overlay.querySelector('.quiz-settings-panel').style.display.includes('block')) {
                this.hide();
            }
        };
        document.addEventListener('keydown', escHandler);
        this.overlay.dataset.escHandler = 'attached';

        // Input submission
        this.inputElement.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (this.isAnimating) {
                    // If showing incorrect answer, move to next word on Enter
                    this.nextWord();
                } else {
                    // Only check answer if input is not empty
                    if (this.inputElement.value.trim().length > 0) {
                        this.checkAnswer();
                    }
                }
            }
        });

        // Settings button
        this.overlay.querySelector('.quiz-settings-btn').addEventListener('click', () => {
            this.showSettings();
        });

        // Settings close button
        this.overlay.querySelector('.quiz-settings-close-btn').addEventListener('click', () => {
            this.hideSettings();
        });

        // Threshold change
        this.overlay.querySelector('#quiz-threshold').addEventListener('change', (e) => {
            const newThreshold = parseInt(e.target.value, 10);
            if (newThreshold >= 1 && newThreshold <= 10) {
                this.quiz.threshold = newThreshold;
                this.quiz.saveSettings();
                this.updateProgress();
            }
        });

        // Reset progress button
        this.overlay.querySelector('.quiz-reset-btn').addEventListener('click', () => {
            if (confirm('Are you sure you want to reset all progress? This cannot be undone.')) {
                this.quiz.resetProgress();
                this.updateProgress();
                this.hideSettings();
                this.nextWord();
            }
        });

        // Click outside settings to close
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        });
    }

    /**
     * Show settings panel
     */
    showSettings() {
        const panel = this.overlay.querySelector('.quiz-settings-panel');
        panel.style.display = 'block';
    }

    /**
     * Hide settings panel
     */
    hideSettings() {
        const panel = this.overlay.querySelector('.quiz-settings-panel');
        panel.style.display = 'none';
    }

    /**
     * Hide the overlay
     */
    hide() {
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
     * Display next word
     */
    nextWord() {
        const item = this.quiz.selectNextWord();

        if (!item) {
            // Quiz complete!
            this.showCompletion();
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

        // Clear input
        this.inputElement.value = '';
        this.inputElement.disabled = false;

        // Clear feedback
        const feedback = this.overlay.querySelector('.quiz-feedback');
        feedback.className = 'quiz-feedback';
        feedback.textContent = '';

        // Update progress
        this.updateProgress();

        // Focus input
        this.inputElement.focus();
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
        this.inputElement.disabled = true;

        const feedback = this.overlay.querySelector('.quiz-feedback');
        feedback.innerHTML = ''; // Clear previous content

        if (correct) {
            feedback.textContent = '✓ Correct!';
            feedback.className = 'quiz-feedback correct show';

            // Automatically move to next word after brief delay
            setTimeout(() => {
                this.nextWord();
            }, 1500);
        } else {
            // Show incorrect feedback with all correct answers and continue button
            feedback.className = 'quiz-feedback incorrect show';

            const incorrectText = document.createElement('div');
            incorrectText.textContent = '✗ Incorrect';
            feedback.appendChild(incorrectText);

            const correctAnswer = document.createElement('div');
            correctAnswer.className = 'quiz-correct-answer';
            // Show all possible answers (strip HTML tags for display)
            const answers = this.quiz.currentWord.answers.map(ans => ans.replace(/<[^>]*>/g, ''));
            if (answers.length === 1) {
                correctAnswer.textContent = `Correct answer: ${answers[0]}`;
            } else {
                correctAnswer.textContent = `Correct answers: ${answers.join(', ')}`;
            }
            feedback.appendChild(correctAnswer);

            const continueBtn = document.createElement('button');
            continueBtn.className = 'quiz-continue-btn';
            continueBtn.textContent = 'Continue (Press Enter)';
            continueBtn.onclick = () => this.nextWord();
            feedback.appendChild(continueBtn);

            // Focus on continue button for accessibility
            setTimeout(() => continueBtn.focus(), 100);
        }
    }

    /**
     * Show completion screen
     */
    showCompletion() {
        const content = this.overlay.querySelector('.quiz-content');
        content.innerHTML = `
            <div class="quiz-completion">
                <div class="quiz-completion-icon">🎉</div>
                <h2>Congratulations!</h2>
                <p>You've memorized all ${this.quiz.allWords.length} words!</p>
                <button class="quiz-restart-btn" type="button">Start Over</button>
            </div>
        `;

        // Setup restart button
        content.querySelector('.quiz-restart-btn').addEventListener('click', () => {
            if (confirm('Reset all progress and start over?')) {
                this.quiz.resetProgress();
                this.hide();
                // Optionally restart immediately
                // this.show();
            }
        });
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

        // Handle button click
        button.addEventListener('click', () => {
            ui.show();
        });
    });
}
