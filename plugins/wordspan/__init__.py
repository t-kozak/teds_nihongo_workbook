"""
Wordspan Plugin for Pelican

Automatically wraps Japanese words in span elements for dictionary functionality.
This plugin should be loaded BEFORE the furigana plugin to preserve word
boundaries for dictionary lookups and other word-level functionality.
"""
from pelican import signals
from .filters import wrap_japanese_words


def process_wordspan(content):
    """
    Process content to wrap Japanese words in spans.

    This is called by Pelican during content processing.
    """
    if hasattr(content, "_content"):
        print(f"[wordspan] Processing content for: {getattr(content, 'source_path', 'unknown')}")
        # Process the content
        content._content = wrap_japanese_words(content._content)


def register():
    """Plugin registration - required by Pelican."""
    signals.content_object_init.connect(process_wordspan)
