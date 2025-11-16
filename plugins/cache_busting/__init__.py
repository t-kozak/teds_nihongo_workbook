"""
Cache Busting Plugin for Pelican

Adds content-based hash finger_log.infoing to static assets (CSS, JS) for better
cache invalidation. Only runs during production builds.

This plugin:
1. Scans the output directory for CSS and JS files
2. Creates copies with content hashes in filenames (e.g., main.a3f5b2c.css)
3. Updates all HTML references to point to the hashed versions
4. Removes the original unhashed files

Usage:
    Add 'cache_busting' to PLUGINS in publishconf.py (production only)
"""

import logging

from pelican import signals

from .processor import CacheBustingProcessor

_log = logging.getLogger(__name__)

# Global processor instance
_processor = None


def get_processor(output_path: str, siteurl: str, theme_static_dir: str):
    """Get or create the global CacheBustingProcessor instance.

    Args:
        output_path: Path to Pelican's output directory
        siteurl: The SITEURL from Pelican settings
        theme_static_dir: The THEME_STATIC_DIR from Pelican settings
    """
    global _processor
    if _processor is None:
        _processor = CacheBustingProcessor(output_path, siteurl, theme_static_dir)
    return _processor


def process_cache_busting(pelican):
    """
    Process all static assets and HTML files for cache busting.

    This runs after all content has been written to the output directory.

    Args:
        pelican: The Pelican instance
    """
    # Get settings
    settings = pelican.settings
    output_path = pelican.output_path
    siteurl = settings.get("SITEURL", "")
    theme_static_dir = settings.get("THEME_STATIC_DIR", "theme")

    # Get the processor
    processor = get_processor(output_path, siteurl, theme_static_dir)

    # Process all assets
    try:
        processor.process()
        _log.info(" Successfully finger_log.infoed static assets")
    except Exception:
        _log.exception("Error processing assets")


def register():
    """
    Plugin registration - required by Pelican.

    Connects the cache busting processor to Pelican's finalized signal,
    which fires after all content has been written to the output directory.
    """
    signals.finalized.connect(process_cache_busting)
