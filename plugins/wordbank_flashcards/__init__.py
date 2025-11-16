"""
Wordbank Flashcards Plugin for Pelican

Converts <wordbank></wordbank> sections in markdown articles into interactive
flashcard widgets with images.

This plugin:
1. Extracts word entries from wordbank sections
2. Propagates them to the site-wide wordbank database using WordBank.propagate()
3. Generates HTML flashcards with images and interactive flip functionality
"""

import logging
from pathlib import Path

from pelican import signals

from .processor import WordbankProcessor

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


# Global processor instance to share cache across all articles
_processor = None
_current_siteurl = None


def get_processor(siteurl: str = "", generate_content: bool = True):
    """Get or create the global WordbankProcessor instance.

    Args:
        siteurl: The SITEURL from Pelican settings
        generate_content: If True, generate images/audio; if False, use cached data only
    """
    global _processor, _current_siteurl
    # Recreate processor if SITEURL has changed or generate_content settings changed
    if _processor is None or _current_siteurl != siteurl:
        _processor = WordbankProcessor(siteurl, not generate_content)
        _current_siteurl = siteurl
    return _processor


def process_wordbank_content(content):
    """
    Process wordbank sections in article content.

    This is connected to the content_object_init signal and runs for each
    content object (article, page, etc.) before it's processed by Pelican.

    Args:
        content: The Pelican content object (Article or Page)
    """
    # Only process if the content has a _content attribute (contains the markdown)
    if not hasattr(content, "_content"):
        return

    # Skip processing for media files
    source_path = getattr(content, "source_path", "")
    if source_path:
        file_ext = Path(source_path).suffix.lower()
        if file_ext in EXCLUDED_EXTENSIONS:
            return

    # Get SITEURL and generate_content from settings
    siteurl = ""
    generate_content = True
    if hasattr(content, "settings"):
        siteurl = content.settings.get("SITEURL", "")
        generate_content = content.settings.get("GENERATE_CONTENT", True)

    # Get the processor with the correct SITEURL and generate_content
    processor = get_processor(siteurl, generate_content)

    # Process the content
    try:
        processed_content = processor.process_content(content._content)
        content._content = processed_content
    except Exception:
        _log.exception(
            f"Error processing wordbank in {getattr(content, 'source_path', 'unknown')}"
        )


def register():
    """
    Plugin registration - required by Pelican.

    Connects the wordbank processing function to Pelican's content_object_init signal,
    which fires when a content object is initialized but before it's fully processed.
    """
    signals.content_object_init.connect(process_wordbank_content)
