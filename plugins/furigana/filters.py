"""Custom Jinja2 filters for adding furigana to Japanese text."""

import re
import fugashi
from markupsafe import Markup


def add_furigana(html_content):
    """
    Add furigana (hiragana readings) above kanji using HTML ruby annotations.

    This filter processes HTML content and wraps kanji words with <ruby> tags,
    adding hiragana readings in <rt> tags above them. Non-kanji text (hiragana,
    katakana, romaji, HTML tags) is preserved as-is.

    Args:
        html_content: HTML string containing Japanese text

    Returns:
        HTML string with ruby annotations added to kanji words

    Example:
        Input: "<p>日本語を勉強します。</p>"
        Output: "<p><ruby>日本語<rt>にほんご</rt></ruby>を<ruby>勉強<rt>べんきょう</rt></ruby>します。</p>"
    """
    if not html_content:
        return html_content

    # Initialize fugashi tagger for morphological analysis
    tagger = fugashi.Tagger()

    # Pattern to match text outside of HTML tags
    # We need to process text nodes but preserve HTML structure
    html_tag_pattern = re.compile(r'(<[^>]+>)')

    # Split content into HTML tags and text segments
    segments = html_tag_pattern.split(str(html_content))

    processed_segments = []
    for segment in segments:
        # If this is an HTML tag, preserve it as-is
        if html_tag_pattern.match(segment):
            processed_segments.append(segment)
        else:
            # This is a text node - process it for furigana
            processed_segments.append(_process_text_for_furigana(segment, tagger))

    result = ''.join(processed_segments)
    return Markup(result)


def _process_text_for_furigana(text, tagger):
    """
    Process a text segment to add furigana to kanji words.

    Args:
        text: Plain text string (not containing HTML tags)
        tagger: Configured fugashi Tagger instance

    Returns:
        Text with ruby annotations added to kanji words
    """
    if not text.strip():
        return text

    # Parse text with morphological analyzer
    words = tagger(text)

    output = []
    for word in words:
        orig = word.surface  # Original text

        # Get katakana reading and convert to hiragana
        kana = word.feature.kana if hasattr(word.feature, 'kana') else None

        if kana:
            hira = _katakana_to_hiragana(kana)
        else:
            # No reading available, use original text
            hira = orig

        # Check if this segment contains kanji
        if _contains_kanji(orig):
            # Wrap with ruby annotation
            output.append(f'<ruby>{orig}<rt>{hira}</rt></ruby>')
        else:
            # No kanji - preserve as-is
            output.append(orig)

    return ''.join(output)


def _katakana_to_hiragana(text):
    """
    Convert katakana characters to hiragana.

    Args:
        text: String containing katakana characters

    Returns:
        String with katakana converted to hiragana
    """
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
    return ''.join(hiragana)


def _contains_kanji(text):
    """
    Check if text contains any kanji characters.

    Kanji Unicode ranges:
    - CJK Unified Ideographs: U+4E00 to U+9FFF
    - CJK Unified Ideographs Extension A: U+3400 to U+4DBF

    Args:
        text: String to check

    Returns:
        True if text contains kanji, False otherwise
    """
    kanji_pattern = re.compile(r'[\u4E00-\u9FFF\u3400-\u4DBF]')
    return bool(kanji_pattern.search(text))
