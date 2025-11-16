"""
Wordspan Plugin for Pelican

Automatically wraps Japanese words in span elements for dictionary functionality.
This plugin should be loaded BEFORE the furigana plugin to preserve word
boundaries for dictionary lookups and other word-level functionality.
"""

import logging
from pathlib import Path

from pelican import signals

from .filters import wrap_japanese_words

_log = logging.getLogger(__name__)

# Media file extensions to exclude from processing
EXCLUDED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".aac",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
    ".flac",
}


def process_wordspan(content):
    """
    Process content to wrap Japanese words in spans.

    This is called by Pelican during content processing.
    """
    if hasattr(content, "_content"):
        # Skip processing for media files
        source_path = getattr(content, "source_path", "")
        if source_path:
            file_ext = Path(source_path).suffix.lower()
            if file_ext in EXCLUDED_EXTENSIONS:
                return

        _log.info(f"Processing content for: {source_path or 'unknown'}")
        # Process the content
        content._content = wrap_japanese_words(content._content)


def register():
    """Plugin registration - required by Pelican."""
    signals.content_object_init.connect(process_wordspan)
