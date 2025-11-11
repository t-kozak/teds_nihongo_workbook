"""
TTS Plugin for Pelican

Converts <tts></tts> sections in markdown articles into audio elements
with text-to-speech generated audio files.

This plugin:
1. Extracts text from TTS sections with optional type and voice attributes
2. Generates audio files using Google's Gemini TTS API
3. Replaces TTS tags with HTML audio elements (inline or full player)
"""

from pelican import signals

from tts_filter.processor import TTSProcessor

# Global processor instance to share cache across all articles
_processor = None
_current_siteurl = None


def get_processor(siteurl: str = "", generate_content: bool = True):
    """Get or create the global TTSProcessor instance.

    Args:
        siteurl: The SITEURL from Pelican settings
        generate_content: If True, generate audio files; if False, use cached files only
    """
    global _processor, _current_siteurl
    # Recreate processor if SITEURL has changed or generate_content settings changed
    if _processor is None or _current_siteurl != siteurl:
        _processor = TTSProcessor(siteurl, not generate_content)
        _current_siteurl = siteurl
    return _processor


def process_tts_content(content):
    """
    Process TTS sections in article content.

    This is connected to the content_object_init signal and runs for each
    content object (article, page, etc.) before it's processed by Pelican.

    Args:
        content: The Pelican content object (Article or Page)
    """
    # Only process if the content has a _content attribute (contains the markdown)
    if not hasattr(content, "_content"):
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
    except Exception as e:
        print(
            f"Error processing TTS in {getattr(content, 'source_path', 'unknown')}: {e}"
        )
        import traceback

        traceback.print_exc()


def register():
    """
    Plugin registration - required by Pelican.

    Connects the TTS processing function to Pelican's content_object_init signal,
    which fires when a content object is initialized but before it's fully processed.
    """
    signals.content_object_init.connect(process_tts_content)
