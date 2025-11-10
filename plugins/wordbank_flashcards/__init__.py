"""
Wordbank Flashcards Plugin for Pelican

Converts <wordbank></wordbank> sections in markdown articles into interactive
flashcard widgets with images.

This plugin:
1. Extracts word entries from wordbank sections
2. Propagates them to the site-wide wordbank database using WordBank.propagate()
3. Generates HTML flashcards with images and interactive flip functionality
"""
from pelican import signals
from .processor import WordbankProcessor


# Global processor instance to share cache across all articles
_processor = None
_current_siteurl = None


def get_processor(siteurl: str = ""):
    """Get or create the global WordbankProcessor instance.

    Args:
        siteurl: The SITEURL from Pelican settings
    """
    global _processor, _current_siteurl
    # Recreate processor if SITEURL has changed
    if _processor is None or _current_siteurl != siteurl:
        _processor = WordbankProcessor(siteurl)
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
    # Check if processing is disabled via config
    if hasattr(content, 'settings'):
        skip_processing = content.settings.get('WORDBANK_SKIP_PROCESSING', False)
        if skip_processing:
            return

    # Only process if the content has a _content attribute (contains the markdown)
    if not hasattr(content, '_content'):
        return

    # Get SITEURL from settings
    siteurl = ""
    if hasattr(content, 'settings'):
        siteurl = content.settings.get('SITEURL', '')

    # Get the processor with the correct SITEURL
    processor = get_processor(siteurl)

    # Process the content
    try:
        processed_content = processor.process_content(content._content)
        content._content = processed_content
    except Exception as e:
        print(f"Error processing wordbank in {getattr(content, 'source_path', 'unknown')}: {e}")
        import traceback
        traceback.print_exc()


def register():
    """
    Plugin registration - required by Pelican.

    Connects the wordbank processing function to Pelican's content_object_init signal,
    which fires when a content object is initialized but before it's fully processed.
    """
    signals.content_object_init.connect(process_wordbank_content)
