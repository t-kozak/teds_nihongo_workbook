AUTHOR = "Ted K"
SITENAME = "Ted's 日本語 Workbook"
SITEURL = ""

PATH = "content"

TIMEZONE = "Australia/Sydney"

DEFAULT_LANG = "en"

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (
    ("Pelican", "https://getpelican.com/"),
    ("Python.org", "https://www.python.org/"),
    ("Jinja2", "https://palletsprojects.com/p/jinja/"),
    ("You can modify those links in your config file", "#"),
)

# Social widget
SOCIAL = (
    ("You can add links in your config file", "#"),
    ("Another social link", "#"),
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True

# Static paths - directories to copy to output
STATIC_PATHS = ["images", "audio"]

# Plugins
PLUGIN_PATHS = ["plugins"]
PLUGINS = [
    "phrasebank",
    "tts_filter",
    "furigana",
    "wordbank_flashcards",
]

# Content Generation Configuration
# Set to True to generate images/audio (production mode)
# Set to False to use cached content only (development mode)
GENERATE_CONTENT = False

# Theme
THEME = "themes/workbook"
