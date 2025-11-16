"""
Japanese text processor plugin for Pelican.

This plugin replaces and combines the functionality of:
- wordspan: Wraps Japanese words in span elements
- furigana: Adds furigana (hiragana readings) to kanji

It uses an LLM-based approach via Marvin Agent to provide:
- Accurate word boundary detection
- Contextual English translations
- Furigana annotations for kanji words

The plugin processes Japanese text in async batches for optimal performance
and caches LLM responses in Redis to significantly reduce API costs.

Environment Variables:
    JAPANESE_PROCESSOR_CACHE_ENABLED: Set to "false" to disable caching (default: "true")
    JAPANESE_PROCESSOR_REDIS_HOST: Redis host (default: "localhost")
    JAPANESE_PROCESSOR_REDIS_PORT: Redis port (default: "6379")
    JAPANESE_PROCESSOR_CACHE_TTL: Cache TTL in seconds (default: 2592000 = 30 days)
"""

import logging
import os
from pathlib import Path

from pelican import signals

from .processor import get_processor

_log = logging.getLogger(__name__)


# File extensions to exclude from processing (media files)
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

# Cache configuration from environment variables
CACHE_ENABLED = (
    os.environ.get("JAPANESE_PROCESSOR_CACHE_ENABLED", "true").lower() != "false"
)
CACHE_TTL = int(os.environ.get("JAPANESE_PROCESSOR_CACHE_TTL", str(86400 * 30)))


def process_content(content):
    """
    Process content to add Japanese word annotations.

    This function is called for each content object during initialization.
    It processes the content HTML to wrap Japanese words with semantic
    annotations including translations and furigana.

    Args:
        content: Pelican content object
    """
    # Only process content objects that have _content attribute
    if not hasattr(content, "_content"):
        return

    # Skip media files
    source_path = getattr(content, "source_path", "")
    if source_path and Path(source_path).suffix.lower() in EXCLUDED_EXTENSIONS:
        return

    # Log processing
    title = getattr(content, "title", "Unknown")
    _log.info(f"\n[japanese_processor] Processing article: {title}")

    try:
        # Get processor instance with cache configuration
        processor = get_processor(
            cache_enabled=CACHE_ENABLED,
            cache_ttl=CACHE_TTL,
        )
        content._content = processor.process_content(content._content)
        _log.info(f"Successfully processed: {title}")

    except Exception:
        _log.exception(f"[japanese_processor] Error processing {title}")
        # Leave content unchanged if processing fails


def register():
    """
    Register the plugin with Pelican.

    This function is called by Pelican to register the plugin's signal handlers.
    The content_object_init signal is used to process each content object
    during the build process.
    """
    _log.info(" Registering Japanese text processor plugin")
    signals.content_object_init.connect(process_content)
