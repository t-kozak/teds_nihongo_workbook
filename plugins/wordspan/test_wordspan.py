"""Test script for the wordspan plugin."""

from filters import wrap_japanese_words


def test_basic_wrapping():
    """Test basic Japanese word wrapping."""
    input_html = "<p>日本語を勉強します。</p>"
    result = wrap_japanese_words(input_html)
    print("Test 1: Basic wrapping")
    print(f"Input:  {input_html}")
    print(f"Output: {result}")
    print()

    # Check that spans are present
    assert 'class="jp-word"' in result
    assert 'data-word=' in result
    assert 'data-reading=' in result
    print("✓ Test 1 passed\n")


def test_mixed_content():
    """Test mixed Japanese and English content."""
    input_html = "<p>Hello 世界！This is a test テスト。</p>"
    result = wrap_japanese_words(input_html)
    print("Test 2: Mixed content")
    print(f"Input:  {input_html}")
    print(f"Output: {result}")
    print()

    # Check that English is preserved
    assert "Hello" in result
    assert "This is a test" in result
    # Check that Japanese is wrapped
    assert 'data-word="世界"' in result
    print("✓ Test 2 passed\n")


def test_html_preservation():
    """Test that HTML tags are preserved."""
    input_html = "<div><strong>日本</strong>の<em>文化</em></div>"
    result = wrap_japanese_words(input_html)
    print("Test 3: HTML preservation")
    print(f"Input:  {input_html}")
    print(f"Output: {result}")
    print()

    # Check that HTML tags are preserved
    assert "<div>" in result
    assert "<strong>" in result
    assert "<em>" in result
    assert "</div>" in result
    print("✓ Test 3 passed\n")


def test_empty_content():
    """Test handling of empty content."""
    result = wrap_japanese_words("")
    print("Test 4: Empty content")
    print(f"Input:  (empty)")
    print(f"Output: {result}")
    assert result == ""
    print("✓ Test 4 passed\n")


def test_no_japanese():
    """Test content with no Japanese."""
    input_html = "<p>This is English text.</p>"
    result = wrap_japanese_words(input_html)
    print("Test 5: No Japanese content")
    print(f"Input:  {input_html}")
    print(f"Output: {result}")
    assert result == input_html
    print("✓ Test 5 passed\n")


if __name__ == "__main__":
    print("Running wordspan plugin tests...\n")
    print("=" * 80)
    print()

    try:
        test_basic_wrapping()
        test_mixed_content()
        test_html_preservation()
        test_empty_content()
        test_no_japanese()

        print("=" * 80)
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
