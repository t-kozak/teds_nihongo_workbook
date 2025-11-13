"""
Phrasebank Processor

Handles parsing of phrasebank sections and generation of semantic HTML
using definition lists (dl/dt/dd) for Japanese phrases with translations.
"""

import hashlib
import json
import re

import fugashi


class PhrasebankProcessor:
    """Processes phrasebank sections in Pelican content."""

    # Pattern to match phrasebank sections
    PHRASEBANK_PATTERN = re.compile(
        r"<phrasebank>(.*?)</phrasebank>", re.DOTALL | re.IGNORECASE
    )

    # Pattern to match individual phrase entries
    # Format: ${phrase in jp}:${en translation} (${context})
    PHRASE_ENTRY_PATTERN = re.compile(
        r"^\s*-\s*(.+?):\s*(.+?)\s*\((.+?)\)\s*$", re.MULTILINE
    )

    def __init__(self, siteurl: str = ""):
        """Initialize the processor.

        Args:
            siteurl: The SITEURL from Pelican settings for generating correct paths
        """
        self.siteurl = siteurl
        # Initialize fugashi tagger for furigana generation
        self.tagger = fugashi.Tagger()  # type: ignore

    def extract_phrasebank_sections(
        self, content: str
    ) -> list[tuple[str, list[tuple[str, str, str]]]]:
        """
        Extract all phrasebank sections from content.

        Args:
            content: The markdown content

        Returns:
            List of tuples: (full_match_text, [(phrase_jp, translation_en, context), ...])
        """
        sections = []
        if not content:
            return []

        for match in self.PHRASEBANK_PATTERN.finditer(content):
            full_match = match.group(0)
            phrasebank_content = match.group(1)

            # Parse individual phrase entries
            phrases = []
            for phrase_match in self.PHRASE_ENTRY_PATTERN.finditer(phrasebank_content):
                phrase_jp = phrase_match.group(1).strip()
                translation_en = phrase_match.group(2).strip()
                context = phrase_match.group(3).strip()
                phrases.append((phrase_jp, translation_en, context))

            if phrases:
                sections.append((full_match, phrases))

        return sections

    def generate_phrase_html(
        self, phrase_jp: str, translation_en: str, context: str
    ) -> str:
        """
        Generate HTML for a single phrase using card-based markup.

        Args:
            phrase_jp: The Japanese phrase
            translation_en: The English translation
            context: The context/description

        Returns:
            HTML string for the phrase card
        """
        # Escape HTML special characters
        translation_escaped = self._escape_html(translation_en)
        context_escaped = self._escape_html(context)

        # Wrap Japanese phrase in <tts> tag for audio generation
        # Don't escape the phrase_jp since it will be processed by TTS plugin
        html = f"""    <div class="phrase-card">
        <div class="phrase-japanese"><p><tts>{phrase_jp}</tts></p></div>
        <div class="phrase-translation"><p>{translation_escaped}</p></div>
        <div class="phrase-context"><p>{context_escaped}</p></div>
    </div>
"""

        return html

    def generate_phrasebank_section_html(
        self, phrases: list[tuple[str, str, str]]
    ) -> str:
        """
        Generate complete HTML section for all phrases.

        Args:
            phrases: List of (phrase_jp, translation_en, context) tuples

        Returns:
            Complete HTML section with card-based grid layout and quiz data
        """
        # Generate individual phrases
        phrases_html = ""
        quiz_data = []

        for phrase_jp, translation_en, context in phrases:
            phrases_html += self.generate_phrase_html(
                phrase_jp, translation_en, context
            )

            # Generate quiz data for this phrase
            # Build answers array with both original phrase and hiragana-only variant
            answers = [phrase_jp]

            # If phrase contains kanji, add hiragana reading as alternative answer
            if self._contains_kanji(phrase_jp):
                # Parse with fugashi to get reading
                words = self.tagger(phrase_jp)

                # Build the hiragana reading
                hiragana_parts = []
                for w in words:
                    # Get katakana reading and convert to hiragana
                    kana = w.feature.kana if hasattr(w.feature, "kana") else None
                    if kana:
                        hiragana = self._katakana_to_hiragana(kana)
                        hiragana_parts.append(hiragana)
                    else:
                        # Fallback to original if no reading available
                        hiragana_parts.append(w.surface)

                hiragana_reading = "".join(hiragana_parts)

                # Only add if different from original
                if hiragana_reading != phrase_jp:
                    answers.append(hiragana_reading)

            # Generate unique ID for this quiz item
            item_id = self._generate_quiz_item_id(translation_en, answers)

            quiz_data.append({
                "id": item_id,
                "question": {
                    "text": translation_en,
                    "imageUrl": ""  # Phrases don't have images
                },
                "answers": answers
            })

        # Generate unique ID for the entire quiz data
        quiz_data_id = self._generate_quiz_data_id(quiz_data)

        # Convert quiz data to JSON for the script tag
        quiz_data_json = json.dumps(quiz_data, ensure_ascii=False)

        # Complete HTML with header, quiz button, phrase list, and quiz data
        complete_html = f"""<div class="phrasebank-section">
    <div class="phrasebank-header">
        <h2>Phrasebank</h2>
        <button class="quiz-button" type="button" data-quiz-data-id="quiz-data-{quiz_data_id}">Quiz</button>
    </div>
    <div class="phrase-list">
{phrases_html}    </div>
    <script type="application/json" class="quiz-data" id="quiz-data-{quiz_data_id}">
        {quiz_data_json}
    </script>
</div>
"""

        return complete_html

    def process_content(self, content: str) -> str:
        """
        Process content: extract phrasebank sections and generate HTML.

        This is the main entry point that replaces phrasebank tags with HTML.

        Args:
            content: The markdown content

        Returns:
            Processed content with phrasebank sections replaced by HTML
        """
        sections = self.extract_phrasebank_sections(content)

        if not sections:
            return content

        # Process each section
        for full_match, phrases in sections:
            # Generate HTML
            html = self.generate_phrasebank_section_html(phrases)

            # Replace the phrasebank section with HTML
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

    @staticmethod
    def _contains_kanji(text: str) -> bool:
        """Check if text contains any kanji characters."""
        kanji_pattern = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")
        return bool(kanji_pattern.search(text))

    @staticmethod
    def _katakana_to_hiragana(text: str) -> str:
        """Convert katakana characters to hiragana."""
        hiragana = []
        for char in text:
            code = ord(char)
            # Katakana range: U+30A0 to U+30FF
            # Hiragana range: U+3040 to U+309F
            # Offset is 0x60 (96)
            if 0x30A0 <= code <= 0x30FF:
                hiragana.append(chr(code - 0x60))
            else:
                hiragana.append(char)
        return "".join(hiragana)

    @staticmethod
    def _generate_quiz_item_id(question_text: str, answers: list[str]) -> str:
        """
        Generate a stable, unique ID for a quiz item based on its content.

        Args:
            question_text: The question text (e.g., English translation)
            answers: List of possible answers

        Returns:
            A hex string hash that uniquely identifies this quiz item
        """
        # Create a deterministic string representation
        content = f"{question_text}|{'|'.join(sorted(answers))}"
        # Generate SHA256 hash and take first 12 characters for brevity
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

    @staticmethod
    def _generate_quiz_data_id(quiz_data: list[dict]) -> str:
        """
        Generate a stable ID for the entire quiz data array.

        Args:
            quiz_data: The complete quiz data array

        Returns:
            A hex string hash of the quiz data
        """
        # Use JSON serialization with sorted keys for deterministic hashing
        content = json.dumps(quiz_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]
