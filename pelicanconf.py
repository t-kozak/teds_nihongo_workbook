import logging

AUTHOR = "Ted K"
SITENAME = "Ted's 日本語 Workbook"
SITEURL = ""

PATH = "content"

TIMEZONE = "Australia/Sydney"

DEFAULT_LANG = "en"


def setup_logging(
    log_file_name: str | None = None,
    file_level: int | None = None,
    console_level: int | None = None,
    log_format: str | None = None,
):
    """
    Configure Python's logging module to output all logs to a file and errors to the console.

    Args:
        log_file_path (str or Path): Path to the log file
        level (int, optional): File logging level. Defaults to logging.INFO.
        console_level (int, optional): Console logging level. Defaults to logging.ERROR.
        log_format (str, optional): Custom log format. If None, uses a default format.

    Returns:
        logging.Logger: Configured logger object
    """

    logging.addLevelName(logging.DEBUG, "🔍")
    logging.addLevelName(logging.INFO, "🆗")
    logging.addLevelName(logging.WARNING, "⚠️ ")
    logging.addLevelName(logging.ERROR, "❌")
    logging.addLevelName(logging.CRITICAL, "🔥")

    # Set up the default format if not provided
    if log_format is None:
        log_format = "%(asctime)s.%(msecs)03d %(levelname)s | %(message)s (%(filename)s:%(lineno)d:%(name)s)"
    formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")

    # Set default levels
    if file_level is None:
        file_level = logging.INFO
    if console_level is None:
        console_level = logging.INFO

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log file specified)
    if log_file_name:
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


# Initialize logging
setup_logging(console_level=logging.INFO)

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
    "wordbank_flashcards",
    "tts_filter",
    "japanese_processor",
    "dialogue_practice",
]

# Content Generation Configuration
# Set to True to generate images/audio (production mode)
# Set to False to use cached content only (development mode)
GENERATE_CONTENT = False

# Theme
THEME = "themes/workbook"
