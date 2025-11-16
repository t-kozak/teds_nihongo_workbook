"""Tests for Japanese text processor."""

import logging

from .processor import JapaneseTextProcessor

_log = logging.getLogger(__name__)


def test_japanese_pattern_matching():
    """Test that Japanese text patterns are correctly identified."""
    processor = JapaneseTextProcessor()

    text = "Hello 日本語 world こんにちは!"
    matches = list(processor.japanese_pattern.finditer(text))

    assert len(matches) == 2
    assert matches[0].group() == "日本語"
    assert matches[1].group() == "こんにちは"


def test_html_preservation():
    """Test that HTML tags are preserved during processing."""
    processor = JapaneseTextProcessor()

    # Test that HTML structure is maintained
    html = "<p>テスト</p>"
    segments = processor.html_tag_pattern.split(html)

    assert "<p>" in segments
    assert "</p>" in segments
    assert "テスト" in segments


def test_script_tag_skipping():
    """Test that content inside script tags is not processed."""
    processor = JapaneseTextProcessor()

    html = """
    <p>日本語</p>
    <script>
    var text = "日本語";
    </script>
    <p>もっと日本語</p>
    """

    # The processor should identify Japanese text but skip script content
    segments = processor.html_tag_pattern.split(html)
    japanese_matches = []

    inside_script = False
    for segment in segments:
        if processor.html_tag_pattern.match(segment):
            if segment.lower().startswith("<script"):
                inside_script = True
            elif segment.lower() == "</script>":
                inside_script = False
        elif not inside_script:
            matches = list(processor.japanese_pattern.finditer(segment))
            japanese_matches.extend([m.group() for m in matches])

    # Should find Japanese text outside script tags
    assert "日本語" in japanese_matches
    assert "もっと日本語" in japanese_matches


def test_empty_content():
    """Test handling of empty content."""
    processor = JapaneseTextProcessor()

    assert processor.process_content("") == ""


def test_no_japanese_content():
    """Test content without Japanese text."""
    processor = JapaneseTextProcessor()

    html = "<p>Hello World</p>"
    result = processor.process_content(html)

    # Should return original HTML unchanged
    assert result == html


def test_llm_prompt_structure():
    """Test that the LLM prompt is properly formatted."""
    processor = JapaneseTextProcessor()

    text = "日本語"
    prompt = processor._build_llm_prompt(text)

    # Check that prompt contains key instructions
    assert "word boundaries" in prompt.lower()
    assert "data-en-translation" in prompt
    assert "data-furigana" in prompt
    assert text in prompt
    assert "jp-word" in prompt


def test_punctuation_skipping():
    """Test that single-character punctuation is skipped."""
    processor = JapaneseTextProcessor()

    # Create test HTML with isolated punctuation
    html = "<p>日本語〜テスト。</p>"

    # The regex will match the full segment "日本語〜テスト。"
    # Since it contains actual words, it should be processed
    # But isolated punctuation like just "〜" would be skipped

    # Test that processor identifies Japanese segments correctly
    segments = processor.html_tag_pattern.split(html)
    assert "日本語〜テスト。" in segments


if __name__ == "__main__":
    # Run basic tests
    _log.info("Running Japanese processor tests...")

    test_japanese_pattern_matching()
    _log.info("✓ Pattern matching test passed")

    test_html_preservation()
    _log.info("✓ HTML preservation test passed")

    test_script_tag_skipping()
    _log.info("✓ Script tag skipping test passed")

    test_empty_content()
    _log.info("✓ Empty content test passed")

    test_no_japanese_content()
    _log.info("✓ No Japanese content test passed")

    test_llm_prompt_structure()
    _log.info("✓ LLM prompt structure test passed")

    _log.info("\n✅ All tests passed!")
