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
        <div class="flashcard-word-jp">{word_escaped}</div>
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

        # Complete HTML with container, CSS, and JavaScript
        complete_html = f"""
<div class="wordbank-container">
    {cards_html}
</div>

<style>
.wordbank-container {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin: 30px 0;
    max-width: 100%;
}}

.flashcard {{
    width: 100%;
    height: 360px;
    perspective: 1000px;
    cursor: pointer;
    position: relative;
    border: 2px solid #ddd;
    border-radius: 10px;
    overflow: hidden;
    background: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: box-shadow 0.3s ease;
}}

.flashcard:hover {{
    box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
}}

.flashcard-front, .flashcard-back {{
    width: 100%;
    height: 100%;
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: center;
    text-align: center;
    overflow: hidden;
}}

.flashcard-front img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: 1;
}}

.flashcard-word-jp {{
    position: relative;
    z-index: 2;
    font-size: 28px;
    font-weight: bold;
    color: #1a202c;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.92);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(4px);
    margin: 0 15px 5px 15px;
}}

.flashcard-back {{
    background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
    padding: 20px;
    overflow-y: auto;
    justify-content: flex-start;
    align-items: flex-start;
    word-wrap: break-word;
    overflow-wrap: break-word;
    box-sizing: border-box;
}}

.flashcard-word-en {{
    font-size: 24px;
    font-weight: bold;
    color: #2c5282;
    margin-bottom: 20px;
    width: 100%;
    text-align: center;
    word-wrap: break-word;
    box-sizing: border-box;
}}

.flashcard-examples-label {{
    font-size: 14px;
    font-weight: 600;
    color: #4a5568;
    margin-bottom: 8px;
    width: 100%;
    box-sizing: border-box;
}}

.flashcard-examples {{
    font-size: 14px;
    color: #2d3748;
    text-align: left;
    padding-left: 20px;
    margin: 0;
    list-style-type: disc;
    width: 100%;
    word-wrap: break-word;
    overflow-wrap: break-word;
    box-sizing: border-box;
}}

.flashcard-examples li {{
    margin-bottom: 10px;
    line-height: 1.6;
    word-wrap: break-word;
    overflow-wrap: break-word;
    box-sizing: border-box;
}}
</style>

<script>
(function() {{
    document.addEventListener('DOMContentLoaded', function() {{
        const flashcards = document.querySelectorAll('.flashcard');

        flashcards.forEach(function(card) {{
            card.addEventListener('click', function() {{
                const front = this.querySelector('.flashcard-front');
                const back = this.querySelector('.flashcard-back');

                if (front.style.display === 'none') {{
                    // Currently showing back, flip to front
                    front.style.display = 'flex';
                    back.style.display = 'none';
                }} else {{
                    // Currently showing front, flip to back
                    // First, reset all other cards to front
                    flashcards.forEach(function(otherCard) {{
                        if (otherCard !== card) {{
                            const otherFront = otherCard.querySelector('.flashcard-front');
                            const otherBack = otherCard.querySelector('.flashcard-back');
                            otherFront.style.display = 'flex';
                            otherBack.style.display = 'none';
                        }}
                    }});

                    // Now flip this card to back
                    front.style.display = 'none';
                    back.style.display = 'flex';
                }}
            }});
        }});
    }});
}})();
</script>
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
