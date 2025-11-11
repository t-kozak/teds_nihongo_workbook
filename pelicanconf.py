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
PLUGINS = ["furigana", "wordbank_flashcards"]

# Wordbank Flashcards Plugin Configuration
# Set to True to disable wordbank processing entirely
WORDBANK_SKIP_PROCESSING = False
# Set to True to skip word propagation (image/audio generation) during development
# This will only generate HTML from existing wordbank cache
WORDBANK_DEV_MODE = True

# Theme
THEME = "themes/workbook"
