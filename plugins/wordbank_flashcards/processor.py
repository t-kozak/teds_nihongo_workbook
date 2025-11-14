"""
Wordbank Flashcard Processor

Handles parsing of wordbank sections, propagation to the wordbank database,
and generation of interactive HTML flashcards.
"""

import asyncio
import hashlib
import json
import re
from pathlib import Path

import fugashi
from tqdm import tqdm

from wordbank import WordBank, WordbankWordDetails

# Batch size for concurrent propagation
PROPAGATE_BATCH_SIZE = 15


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

    def __init__(self, siteurl: str = "", dev_mode: bool = False):
        """Initialize the processor with a WordBank instance.

        Args:
            siteurl: The SITEURL from Pelican settings for generating correct paths
            dev_mode: If True, skip word propagation and only generate HTML from cache
        """
        self.wordbank = WordBank()
        self.siteurl = siteurl
        self.dev_mode = dev_mode
        # Cache to store propagated words during first pass
        self._propagated_cache = {}
        # Initialize fugashi tagger for furigana generation
        self.tagger = fugashi.Tagger()  # type: ignore

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

    async def propagate_words(
        self, words: list[tuple[str, str, str]]
    ) -> list[WordbankWordDetails]:
        """
        Propagate words to the wordbank database using async batch processing.

        Args:
            words: List of (japanese_word, english_translation, context) tuples

        Returns:
            List of WordbankWordDetails objects
        """
        results = []

        # Process words in batches for better concurrency control
        with tqdm(
            total=len(words),
            desc="Processing wordbank entries",
            unit="word",
            leave=False,
        ) as pbar:
            for i in range(0, len(words), PROPAGATE_BATCH_SIZE):
                batch = words[i : i + PROPAGATE_BATCH_SIZE]
                batch_tasks = []

                for japanese_word, english_translation, context in batch:
                    cache_key = (japanese_word, english_translation)

                    # Check if we already propagated this word in this session
                    if cache_key in self._propagated_cache:
                        results.append(self._propagated_cache[cache_key])
                        pbar.update(1)
                        continue

                    # In dev mode, only fetch from cache without propagating
                    if self.dev_mode:
                        details = self.wordbank.get(japanese_word, english_translation)
                        if details is None:
                            # Word not in cache - skip image/audio generation in dev mode
                            # Create minimal details object for HTML generation
                            details = WordbankWordDetails(
                                word=japanese_word,
                                en_translation=english_translation,
                                language_code="ja",  # Default to Japanese
                                examples=[],
                                description=context,
                                image_description="",  # Empty in dev mode
                            )
                        # Cache the result
                        self._propagated_cache[cache_key] = details
                        results.append(details)
                        pbar.update(1)
                    else:
                        # Production mode: Propagate the word (generates images/audio) asynchronously
                        batch_tasks.append(
                            (
                                cache_key,
                                self.wordbank.propagate(
                                    japanese_word, english_translation, context
                                ),
                            )
                        )

                # Wait for all tasks in the batch to complete
                if batch_tasks:
                    batch_results = await asyncio.gather(
                        *[task for _, task in batch_tasks]
                    )
                    for (cache_key, _), details in zip(batch_tasks, batch_results):
                        # Cache the result
                        self._propagated_cache[cache_key] = details
                        results.append(details)
                        pbar.update(1)

        return results

    def generate_flashcard_html(self, details: WordbankWordDetails) -> str:
        """
        Generate HTML for a single flashcard.

        Args:
            details: The word details

        Returns:
            HTML string for the flashcard, or empty string if image file doesn't exist
        """
        # Check if image file exists - skip flashcard if not
        if details.image_file:
            image_file_path = (
                Path(__file__).parent.parent.parent
                / "content"
                / "images"
                / "wordbank"
                / details.image_file
            )
            if not image_file_path.exists():
                print(
                    f"Warning: Skipping flashcard for '{details.word}' - image file not found: {details.image_file}"
                )
                return ""
            image_path = f"{self.siteurl}/images/wordbank/{details.image_file}"
        else:
            # No image file specified - skip this flashcard
            print(
                f"Warning: Skipping flashcard for '{details.word}' - no image file specified"
            )
            return ""

        # Escape HTML special characters
        word_escaped = self._escape_html(details.word)
        en_translation_escaped = self._escape_html(details.en_translation)

        # Generate audio button HTML only if audio file exists on disk
        audio_button = ""
        if details.audio_file:
            audio_file_path = (
                Path(__file__).parent.parent.parent
                / "content"
                / "audio"
                / "wordbank"
                / details.audio_file
            )
            if audio_file_path.exists():
                audio_path = f"{self.siteurl}/audio/wordbank/{details.audio_file}"
                speaker_icon_path = f"{self.siteurl}/images/audio-speaker.svg"
                audio_button = f"""<audio class="flashcard-audio" style="display: none;">
            <source src="{audio_path}" type="audio/aac">
            Your browser does not support the audio element.
        </audio>
        <button class="flashcard-audio-btn" aria-label="Play pronunciation" onclick="event.stopPropagation();">
            <img src="{speaker_icon_path}" alt="Play" width="16" height="16" style="pointer-events: none;">
        </button>"""
            else:
                print(
                    f"Warning: Audio file not found for '{details.word}' - skipping audio button: {details.audio_file}"
                )

        # Generate example sentences HTML
        examples_html = ""
        if details.examples:
            examples_html = (
                "<div class='flashcard-examples-label'>Example sentences:</div>"
            )
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
        # Generate individual flashcards, filtering out empty ones (missing images)
        cards_html = ""
        quiz_data = []

        for details in word_details_list:
            card_html = self.generate_flashcard_html(details)
            if card_html:  # Only add non-empty flashcards
                cards_html += card_html

                # Prepare quiz data for this word in new generalized format
                image_url = (
                    f"{self.siteurl}/images/wordbank/{details.image_file}"
                    if details.image_file
                    else ""
                )

                # Build answers array with both kanji and hiragana-only variants
                answers = [details.word]

                # If word contains kanji, add hiragana reading as alternative answer
                if self._contains_kanji(details.word):
                    # Parse with fugashi to get reading
                    words = self.tagger(details.word)

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
                    if hiragana_reading != details.word:
                        answers.append(hiragana_reading)

                # Generate unique ID for this quiz item
                item_id = self._generate_quiz_item_id(details.en_translation, answers)

                quiz_data.append(
                    {
                        "id": item_id,
                        "question": {
                            "text": details.en_translation,
                            "imageUrl": image_url,
                        },
                        "answers": answers,
                    }
                )

        # Generate unique ID for the entire quiz data
        quiz_data_id = self._generate_quiz_data_id(quiz_data)

        # Convert quiz data to JSON for the script tag
        quiz_data_json = json.dumps(quiz_data, ensure_ascii=False)

        # Complete HTML with header, quiz button, container, and data script
        complete_html = f"""
<div class="wordbank-section">
    <button class="quiz-button" type="button" data-quiz-data-id="quiz-data-{quiz_data_id}">Quiz</button>
    <div class="wordbank-container">
        {cards_html}
    </div>
    <script type="application/json" class="quiz-data" id="quiz-data-{quiz_data_id}">
        {quiz_data_json}
    </script>
</div>
"""

        return complete_html

    async def process_content_async(self, content: str) -> str:
        """
        Process content: extract wordbank sections, propagate words, and generate HTML.

        This is the async main entry point that combines both passes with concurrent processing.

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
            # First pass: propagate words (async with batching)
            word_details_list = await self.propagate_words(words)

            # Second pass: generate HTML
            html = self.generate_flashcard_section_html(word_details_list)

            # Replace the wordbank section with HTML
            content = content.replace(full_match, html)

        return content

    def process_content(self, content: str) -> str:
        """
        Process content: extract wordbank sections, propagate words, and generate HTML.

        This is the sync wrapper that runs the async processing.

        Args:
            content: The markdown content

        Returns:
            Processed content with wordbank sections replaced by HTML flashcards
        """
        # Check if there's already a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # We're already in an async context, create a new loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, self.process_content_async(content)
                )
                return future.result()
        else:
            # No event loop running, we can safely use asyncio.run
            return asyncio.run(self.process_content_async(content))

    def _generate_furigana_text(self, word: str) -> str:
        """
        Generate furigana text for a Japanese word.

        If the word contains kanji, returns format: "kanji (hiragana)"
        If no kanji, returns just the word.

        Args:
            word: Japanese word (may contain kanji, hiragana, katakana)

        Returns:
            Formatted string with furigana, e.g., "意味 (いみ)" or just "です"
        """
        # Check if word contains kanji
        if not self._contains_kanji(word):
            return word

        # Parse with fugashi to get reading
        words = self.tagger(word)

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

        # Return formatted as "kanji (hiragana)"
        return f"{word} ({hiragana_reading})"

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
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

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
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
