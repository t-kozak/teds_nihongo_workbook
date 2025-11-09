"""
SayHi Plugin for Pelican

Registers custom Jinja2 filters for greeting functionality.
"""
from pelican import signals
from .filters import say_hi


def add_filters(pelican):
    """Add custom filters to Pelican's Jinja environment."""
    pelican.env.filters.update({
        'say_hi': say_hi,
    })


def register():
    """Plugin registration - required by Pelican."""
    signals.generator_init.connect(add_filters)
