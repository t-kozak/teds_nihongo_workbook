"""Test script for the wordspan plugin."""

import logging

from filters import wrap_japanese_words

_log = logging.getLogger(__name__)


def test_basic_wrapping():
    """Test basic Japanese word wrapping."""
    input_html = "<p>日本語を勉強します。</p>"
    result = wrap_japanese_words(input_html)
    _log.info("Test 1: Basic wrapping")
    _log.info(f"Input:  {input_html}")
    _log.info(f"Output: {result}")

    # Check that spans are present
    assert 'class="jp-word"' in result
    assert "data-word=" in result
    assert "data-reading=" in result
    _log.info("✓ Test 1 passed\n")


def test_mixed_content():
    """Test mixed Japanese and English content."""
    input_html = "<p>Hello 世界！This is a test テスト。</p>"
    result = wrap_japanese_words(input_html)
    _log.info("Test 2: Mixed content")
    _log.info(f"Input:  {input_html}")
    _log.info(f"Output: {result}")

    # Check that English is preserved
    assert "Hello" in result
    assert "This is a test" in result
    # Check that Japanese is wrapped
    assert 'data-word="世界"' in result
    _log.info("✓ Test 2 passed\n")


def test_html_preservation():
    """Test that HTML tags are preserved."""
    input_html = "<div><strong>日本</strong>の<em>文化</em></div>"
    result = wrap_japanese_words(input_html)
    _log.info("Test 3: HTML preservation")
    _log.info(f"Input:  {input_html}")
    _log.info(f"Output: {result}")

    # Check that HTML tags are preserved
    assert "<div>" in result
    assert "<strong>" in result
    assert "<em>" in result
    assert "</div>" in result
    _log.info("✓ Test 3 passed\n")


def test_empty_content():
    """Test handling of empty content."""
    result = wrap_japanese_words("")
    _log.info("Test 4: Empty content")
    _log.info("Input:  (empty)")
    _log.info(f"Output: {result}")
    assert result == ""
    _log.info("✓ Test 4 passed\n")


def test_no_japanese():
    """Test content with no Japanese."""
    input_html = "<p>This is English text.</p>"
    result = wrap_japanese_words(input_html)
    _log.info("Test 5: No Japanese content")
    _log.info(f"Input:  {input_html}")
    _log.info(f"Output: {result}")
    assert result == input_html
    _log.info("✓ Test 5 passed\n")


if __name__ == "__main__":
    _log.info("Running wordspan plugin tests...\n")
    _log.info("=" * 80)

    try:
        test_basic_wrapping()
        test_mixed_content()
        test_html_preservation()
        test_empty_content()
        test_no_japanese()

        _log.info("=" * 80)
        _log.info("\n✓ All tests passed!")
    except Exception:
        _log.exception("\n✗ Test failed with error")
