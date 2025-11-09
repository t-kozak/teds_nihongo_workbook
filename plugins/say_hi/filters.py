"""Custom Jinja2 filters for Ted's Nihongo Workbook."""


def say_hi(name):
    """
    A simple greeting filter.

    Args:
        name: The name to greet

    Returns:
        A greeting string in the format "Hello {name}"

    Example:
        {{ "Ted" | say_hi }}
        Output: Hello Ted
    """
    return f"Hello {name}"
