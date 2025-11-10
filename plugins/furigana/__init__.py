"""
Furigana Plugin for Pelican

Registers custom Jinja2 filters for adding furigana (hiragana readings)
above kanji characters using HTML ruby annotations.
"""
from pelican import signals
from .filters import add_furigana


def add_filters(pelican):
    """Add custom filters to Pelican's Jinja environment."""
    pelican.env.filters.update({
        'add_furigana': add_furigana,
    })


def register():
    """Plugin registration - required by Pelican."""
    signals.generator_init.connect(add_filters)
