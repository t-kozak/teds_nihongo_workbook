"""
Wordbank Flashcard Processor

Handles parsing of wordbank sections, propagation to the wordbank database,
and generation of interactive HTML flashcards.
"""

import re

from tqdm import tqdm

from wordbank import WordBank, WordbankWordDetails


class WordbankProcessor:
    """Processes wordbank sections in Pelican content."""

    # Pattern to match wordbank sections
    WORDBANK_PATTERN = re.compile(
        r"<wordbank>(.*?)</wordbank>", re.DOTALL | re.IGNORECASE
    )

    # Pattern to match individual word entries
    # Format: - ${japanese_word}: ${english_translation} (${context})
    WORD_ENTRY_PATTERN = re.compile(
        r"^\s*-\s*(.+?):\s*(.+?)\s*\((.+?)\)\s*$", re.MULTILINE
    )

    def __init__(self):
        """Initialize the processor with a WordBank instance."""
        self.wordbank = WordBank()
        # Cache to store propagated words during first pass
        self._propagated_cache = {}

    def extract_wordbank_sections(
        self, content: str
    ) -> list[tuple[str, list[tuple[str, str, str]]]]:
        """
        Extract all wordbank sections from content.

        Args:
            content: The markdown content

        Returns:
            List of tuples: (full_match_text, [(word, translation, context), ...])
        """
        sections = []
        if not content:
            return []

        for match in self.WORDBANK_PATTERN.finditer(content):
            full_match = match.group(0)
            wordbank_content = match.group(1)

            # Parse individual word entries
            words = []
            for word_match in self.WORD_ENTRY_PATTERN.finditer(wordbank_content):
                japanese_word = word_match.group(1).strip()
                english_translation = word_match.group(2).strip()
                context = word_match.group(3).strip()
                words.append((japanese_word, english_translation, context))

            if words:
                sections.append((full_match, words))

        return sections

    def propagate_words(
        self, words: list[tuple[str, str, str]]
    ) -> list[WordbankWordDetails]:
        """
        Propagate words to the wordbank database.

        Args:
            words: List of (japanese_word, english_translation, context) tuples

        Returns:
            List of WordbankWordDetails objects
        """
        results = []

        # Use tqdm to show progress
        for japanese_word, english_translation, context in tqdm(
            words, desc="Processing wordbank entries", unit="word", leave=False
        ):
            cache_key = (japanese_word, english_translation)

            # Check if we already propagated this word in this session
            if cache_key in self._propagated_cache:
                results.append(self._propagated_cache[cache_key])
                continue

            # Propagate the word (this handles caching internally)
            details = self.wordbank.propagate(
                japanese_word, english_translation, context
            )

            # Cache the result
            self._propagated_cache[cache_key] = details
            results.append(details)

        return results

    def generate_flashcard_html(self, details: WordbankWordDetails) -> str:
        """
        Generate HTML for a single flashcard.

        Args:
            details: The word details

        Returns:
            HTML string for the flashcard
        """
        # Determine image path
        if details.image_file:
            image_path = f"/images/wordbank/{details.image_file}"
        else:
            # Fallback to a placeholder or empty image
            image_path = "/images/wordbank/placeholder.jpg"

        # Escape HTML special characters
        word_escaped = self._escape_html(details.word)
        en_translation_escaped = self._escape_html(details.en_translation)

        # Generate audio button HTML if audio file exists
        audio_button = ""
        if details.audio_file:
            audio_path = f"/audio/wordbank/{details.audio_file}"
            audio_button = f"""<audio class="flashcard-audio" style="display: none;">
            <source src="{audio_path}" type="audio/aac">
            Your browser does not support the audio element.
        </audio>
        <button class="flashcard-audio-btn" aria-label="Play pronunciation">
            <svg focusable="false" width="16" height="16" viewBox="0 0 24 24">
                <path d="M3 9v6h4l5 5V4L7 9H3zm7-.17v6.34L7.83 13H5v-2h2.83L10 8.83zM16.5 12A4.5 4.5 0 0 0 14 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02z"></path>
                <path d="M14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77 0-4.28-2.99-7.86-7-8.77z"></path>
            </svg>
        </button>"""

        # Generate example sentences HTML
        examples_html = ""
        if details.examples:
            examples_html = "<div class='flashcard-examples-label'>Example sentences:</div>"
            examples_html += "<ul class='flashcard-examples'>"
            for example in details.examples:
                example_escaped = self._escape_html(example)
                examples_html += f"<li>{example_escaped}</li>"
            examples_html += "</ul>"

        html = f"""
<div class="flashcard" data-word="{word_escaped}" data-translation="{en_translation_escaped}">
    <div class="flashcard-front">
        <img src="{image_path}" alt="{en_translation_escaped}" loading="lazy">
        <div class="flashcard-word-jp">{word_escaped}{audio_button}</div>
    </div>
    <div class="flashcard-back" style="display: none;">
        <div class="flashcard-word-en">{en_translation_escaped}</div>
        {examples_html}
    </div>
</div>"""

        return html

    def generate_flashcard_section_html(
        self, word_details_list: list[WordbankWordDetails]
    ) -> str:
        """
        Generate complete HTML section for all flashcards.

        Args:
            word_details_list: List of WordbankWordDetails objects

        Returns:
            Complete HTML section with container, cards, CSS, and JavaScript
        """
        # Generate individual flashcards
        cards_html = ""
        for details in word_details_list:
            cards_html += self.generate_flashcard_html(details)

        # Complete HTML with container
        complete_html = f"""
<div class="wordbank-container">
    {cards_html}
</div>
"""

        return complete_html

    def process_content(self, content: str) -> str:
        """
        Process content: extract wordbank sections, propagate words, and generate HTML.

        This is the main entry point that combines both passes.

        Args:
            content: The markdown content

        Returns:
            Processed content with wordbank sections replaced by HTML flashcards
        """
        sections = self.extract_wordbank_sections(content)

        if not sections:
            return content

        # Process each section
        for full_match, words in sections:
            # First pass: propagate words
            word_details_list = self.propagate_words(words)

            # Second pass: generate HTML
            html = self.generate_flashcard_section_html(word_details_list)

            # Replace the wordbank section with HTML
            content = content.replace(full_match, html)

        return content

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
