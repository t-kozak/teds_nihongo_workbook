"""
Phrasebank Plugin for Pelican

This plugin processes <phrasebank> tags in content and converts them into
semantic HTML definition lists (dl/dt/dd) with integrated TTS support.
"""

from pelican import signals

from .processor import PhrasebankProcessor


def process_phrasebank(content):
    """
    Process phrasebank sections in content.

    This is called by Pelican during content processing.
    """
    if hasattr(content, "_content"):
        # Get SITEURL from settings
        siteurl = content.settings.get("SITEURL", "")

        # Create processor instance
        processor = PhrasebankProcessor(siteurl=siteurl)

        # Process the content
        content._content = processor.process_content(content._content)


def register():
    """Register the plugin with Pelican."""
    signals.content_object_init.connect(process_phrasebank)
