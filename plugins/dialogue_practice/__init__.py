"""
Dialogue Practice Plugin for Pelican

Converts <dialogue_practice> tags into interactive buttons for AI conversation practice.
"""

import logging
from pelican import signals
from .processor import get_processor

_log = logging.getLogger(__name__)


def process_dialogue_practice(content_object):
    """Process dialogue practice tags in content."""
    if not hasattr(content_object, "_content"):
        return

    # Get SITEURL from settings
    siteurl = content_object.settings.get("SITEURL", "")
    generate_content = content_object.settings.get("GENERATE_CONTENT", False)

    # Get the processor instance
    processor = get_processor(siteurl, generate_content)

    # Process the content
    try:
        original_content = content_object._content
        processed_content = processor.process_content(original_content)
        content_object._content = processed_content

        if original_content != processed_content:
            _log.info(
                f"🗣️  Processed dialogue practice sections in {content_object.source_path}"
            )
    except Exception as e:
        _log.error(
            f"Error processing dialogue practice in {content_object.source_path}: {e}"
        )


def register():
    """Register the plugin with Pelican."""
    signals.content_object_init.connect(process_dialogue_practice)
    _log.info("Dialogue Practice plugin registered")
