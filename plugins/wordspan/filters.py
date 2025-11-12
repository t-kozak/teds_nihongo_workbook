"""Custom Jinja2 filters for wrapping Japanese words in span elements."""

import json
import re
from pathlib import Path

import fugashi
from markupsafe import Markup

# Global dictionary cache for translations (lazy loaded)
_translations_cache = None


def _load_translations():
    """
    Lazy load the Japanese-English translation dictionary.

    Returns:
        Dict mapping Japanese words (in kana/kanji) to lists of English translations
    """
    global _translations_cache

    if _translations_cache is not None:
        return _translations_cache

    translations_file = Path(__file__).parent.parent.parent / "data" / "ja-translations.json"

    print(f"[wordspan] Loading translations from {translations_file}")

    try:
        with open(translations_file, 'r', encoding='utf-8') as f:
            _translations_cache = json.load(f)
        print(f"[wordspan] Loaded {len(_translations_cache):,} translation entries")
    except FileNotFoundError:
        print(f"[wordspan] Warning: Translation file not found at {translations_file}")
        _translations_cache = {}
    except json.JSONDecodeError as e:
        print(f"[wordspan] Warning: Failed to parse translations JSON: {e}")
        _translations_cache = {}

    return _translations_cache


def wrap_japanese_words(html_content):
    """
    Wrap each Japanese word in a <span> element for word-level functionality.

    This filter processes HTML content and wraps each distinct Japanese word
    with a <span class="jp-word"> tag for styling and JavaScript hooks.

    This should be applied BEFORE the furigana filter, as it preserves the
    text content for subsequent processing.

    Args:
        html_content: HTML string containing Japanese text

    Returns:
        HTML string with Japanese words wrapped in span elements

    Example:
        Input: "<p>日本語を勉強します。</p>"
        Output: "<p><span class="jp-word">日本</span><span class="jp-word">語</span><span class="jp-word">を</span><span class="jp-word">勉強</span><span class="jp-word">し</span><span class="jp-word">ます</span>。</p>"
    """
    if not html_content:
        print("[wordspan] Empty content, skipping")
        return html_content

    print(f"[wordspan] Processing content (length: {len(str(html_content))} chars)")

    # Load translations dictionary (lazy loaded on first use)
    translations = _load_translations()

    # Initialize fugashi tagger for morphological analysis
    tagger = fugashi.Tagger()  # type:ignore

    # Pattern to match text outside of HTML tags
    html_tag_pattern = re.compile(r"(<[^>]+>)")

    # Split content into HTML tags and text segments
    segments = html_tag_pattern.split(str(html_content))

    # Counter for unique word IDs across the entire content
    word_counter = {"count": 0}

    processed_segments = []
    for segment in segments:
        # If this is an HTML tag, preserve it as-is
        if html_tag_pattern.match(segment):
            processed_segments.append(segment)
        else:
            # This is a text node - process it for word wrapping
            processed_segments.append(
                _process_text_for_wordspan(segment, tagger, word_counter, translations)
            )

    result = "".join(processed_segments)
    print(f"[wordspan] Wrapped {word_counter['count']} Japanese words")
    return Markup(result)


def _process_text_for_wordspan(text, tagger, word_counter, translations):
    """
    Process a text segment to wrap Japanese words in spans.

    Args:
        text: Plain text string (not containing HTML tags)
        tagger: Configured fugashi Tagger instance
        word_counter: Dict with 'count' key for tracking unique word IDs
        translations: Dict mapping Japanese words to English translations

    Returns:
        Text with Japanese words wrapped in span elements
    """
    if not text.strip():
        return text

    # Split text into Japanese and non-Japanese segments
    # Japanese characters include: Hiragana, Katakana, Kanji, and Japanese punctuation
    japanese_pattern = re.compile(
        r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]+"
    )

    output = []
    last_end = 0

    for match in japanese_pattern.finditer(text):
        # Add any non-Japanese text before this match (preserve as-is)
        if match.start() > last_end:
            output.append(text[last_end : match.start()])

        # Process the Japanese segment with fugashi
        japanese_segment = match.group()
        output.append(_process_japanese_segment(japanese_segment, tagger, word_counter, translations))

        last_end = match.end()

    # Add any remaining non-Japanese text
    if last_end < len(text):
        output.append(text[last_end:])

    return "".join(output)


def _try_merge_tokens(words, index):
    """
    Try to merge current token with following tokens to create more meaningful units.

    For example, merge verb stems with auxiliary verbs:
    - 行き + ます → 行きます
    - 食べ + まし + た → 食べました
    - 勉強 + し + ます → 勉強します

    Args:
        words: List of fugashi word tokens
        index: Current index in the words list

    Returns:
        Tuple of (merged_surface, merged_lemma, skip_count)
        - merged_surface: Combined surface form, or original if no merge
        - merged_lemma: Combined lemma form, or None if no merge
        - skip_count: Number of additional tokens to skip (0 if no merge)
    """
    if index >= len(words):
        return words[index].surface, None, 0

    current = words[index]

    # Get POS tags safely
    try:
        current_pos1 = current.feature.pos1 if hasattr(current.feature, 'pos1') else None
        current_lemma = current.feature.lemma if hasattr(current.feature, 'lemma') else None
    except (AttributeError, IndexError):
        return current.surface, None, 0

    # Pattern 1: Verb + auxiliary verb (ます/ました/etc)
    # Example: 行き (動詞) + ます (助動詞)
    if current_pos1 == '動詞' and index + 1 < len(words):
        next_word = words[index + 1]
        try:
            next_pos1 = next_word.feature.pos1 if hasattr(next_word.feature, 'pos1') else None
            next_lemma = next_word.feature.lemma if hasattr(next_word.feature, 'lemma') else None
        except (AttributeError, IndexError):
            return current.surface, None, 0

        # Merge verb + ます/た/etc
        if next_pos1 == '助動詞':
            merged_surface = current.surface + next_word.surface
            merged_lemma = current_lemma  # Use the verb's base form for lookup

            # Check if there's a た after ます (e.g., ました)
            if index + 2 < len(words):
                third_word = words[index + 2]
                try:
                    third_pos1 = third_word.feature.pos1 if hasattr(third_word.feature, 'pos1') else None
                except (AttributeError, IndexError):
                    return merged_surface, merged_lemma, 1

                if third_pos1 == '助動詞':
                    merged_surface = merged_surface + third_word.surface
                    return merged_surface, merged_lemma, 2

            return merged_surface, merged_lemma, 1

    # Pattern 2: Noun + する verb pattern
    # Example: 勉強 (名詞) + し (動詞) + ます (助動詞)
    if current_pos1 == '名詞' and index + 1 < len(words):
        next_word = words[index + 1]
        try:
            next_pos1 = next_word.feature.pos1 if hasattr(next_word.feature, 'pos1') else None
            next_lemma = next_word.feature.lemma if hasattr(next_word.feature, 'lemma') else None
        except (AttributeError, IndexError):
            return current.surface, None, 0

        # Check if next is する (為る)
        if next_pos1 == '動詞' and next_lemma == '為る':
            merged_surface = current.surface + next_word.surface
            # Use the noun as the lemma (e.g., "勉強" not "勉強する")
            # Many dictionaries have the noun form, not the verb form
            merged_lemma = current_lemma if current_lemma else current.surface

            # Check if there's an auxiliary after する (e.g., ます)
            if index + 2 < len(words):
                third_word = words[index + 2]
                try:
                    third_pos1 = third_word.feature.pos1 if hasattr(third_word.feature, 'pos1') else None
                except (AttributeError, IndexError):
                    return merged_surface, merged_lemma, 1

                if third_pos1 == '助動詞':
                    merged_surface = merged_surface + third_word.surface

                    # Check for た after ます
                    if index + 3 < len(words):
                        fourth_word = words[index + 3]
                        try:
                            fourth_pos1 = fourth_word.feature.pos1 if hasattr(fourth_word.feature, 'pos1') else None
                        except (AttributeError, IndexError):
                            return merged_surface, merged_lemma, 2

                        if fourth_pos1 == '助動詞':
                            merged_surface = merged_surface + fourth_word.surface
                            return merged_surface, merged_lemma, 3

                    return merged_surface, merged_lemma, 2

            return merged_surface, merged_lemma, 1

    # No merge pattern matched
    return current.surface, None, 0


def _process_japanese_segment(text, tagger, word_counter, translations):
    """
    Process a Japanese text segment to wrap each word in a span.

    Args:
        text: Japanese text string (hiragana, katakana, kanji)
        tagger: Configured fugashi Tagger instance
        word_counter: Dict with 'count' key for tracking unique word IDs
        translations: Dict mapping Japanese words to English translations

    Returns:
        Text with each word wrapped in a span element
    """
    # Parse text with morphological analyzer
    words = list(tagger(text))

    output = []
    i = 0
    while i < len(words):
        word = words[i]
        orig = word.surface  # Original text

        # Check if this is actually a word (not just punctuation)
        if _is_japanese_word(orig):
            # Check if we should merge this token with the next one (e.g., verb + auxiliary)
            merged_surface, merged_lemma, skip_count = _try_merge_tokens(words, i)

            if skip_count > 0:
                # We merged tokens, use the merged forms
                orig = merged_surface
                lemma = merged_lemma
                i += skip_count  # Skip the merged tokens
            else:
                # Single token, get its lemma
                try:
                    lemma = word.feature.lemma if hasattr(word.feature, 'lemma') else None
                except (AttributeError, IndexError):
                    lemma = None

            word_counter["count"] += 1

            # Get the reading (kana) for dictionary lookup
            # Try to get the reading from fugashi feature, fallback to surface
            try:
                reading = word.feature.kana  # Reading in katakana
                # Convert katakana to hiragana for better dictionary matching
                reading = _katakana_to_hiragana(reading) if reading else orig
            except (AttributeError, IndexError):
                reading = orig

            # Get lemma in kana form (better for dictionary lookup than kanji lemma)
            try:
                lemma_kana = word.feature.kanaBase if hasattr(word.feature, 'kanaBase') else None
                lemma_kana = _katakana_to_hiragana(lemma_kana) if lemma_kana else None
            except (AttributeError, IndexError):
                lemma_kana = None

            # Look up English translations
            # Try multiple forms in order of preference:
            # 1. Original surface form (may include kanji or conjugated form)
            # 2. Lemma in kana (base form in hiragana - most reliable for dictionary lookup)
            # 3. Lemma in kanji (base form)
            # 4. Reading (hiragana pronunciation of surface)
            english_translations = translations.get(orig)
            if not english_translations and lemma_kana and lemma_kana != orig:
                english_translations = translations.get(lemma_kana)
            if not english_translations and lemma and lemma != orig and lemma != lemma_kana:
                english_translations = translations.get(lemma)
            if not english_translations and reading and reading != orig and reading != lemma_kana:
                english_translations = translations.get(reading)
            if not english_translations:
                english_translations = []

            # Build the span element with translations
            if english_translations:
                # Escape pipe characters and quotes in translations for HTML attribute
                escaped_translations = [t.replace('"', '&quot;').replace('|', '&#124;') for t in english_translations]
                translation_attr = f' data-en-translation="{"|".join(escaped_translations)}"'
                output.append(f'<span class="jp-word"{translation_attr}>{orig}</span>')
            else:
                # No translation found
                output.append(f'<span class="jp-word">{orig}</span>')
        else:
            # Punctuation or non-word - preserve as-is
            output.append(orig)

        i += 1

    return "".join(output)


def _katakana_to_hiragana(text):
    """
    Convert katakana characters to hiragana.

    Args:
        text: String potentially containing katakana

    Returns:
        String with katakana converted to hiragana
    """
    if not text:
        return text

    result = []
    for char in text:
        code = ord(char)
        # Katakana range: 0x30A0-0x30FF
        # Hiragana range: 0x3040-0x309F
        # Offset: 0x60
        if 0x30A0 <= code <= 0x30FF:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return ''.join(result)


def _is_japanese_word(text):
    """
    Check if text is a Japanese word (not just punctuation).

    Args:
        text: String to check

    Returns:
        True if text contains Japanese word characters, False otherwise
    """
    # Check for hiragana, katakana, or kanji
    word_pattern = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]")
    return bool(word_pattern.search(text))
