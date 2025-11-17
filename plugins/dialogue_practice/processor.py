"""
Dialogue Practice Processor

Handles parsing of dialogue practice sections and generation of interactive HTML.
"""

import hashlib
import json
import logging
from bs4 import BeautifulSoup

_log = logging.getLogger(__name__)

# Singleton pattern for processor
_processor = None
_current_siteurl = None


class DialoguePracticeProcessor:
    """Processes dialogue practice sections in Pelican content."""

    def __init__(self, siteurl: str = "", generate_content: bool = False):
        """Initialize the processor.

        Args:
            siteurl: The SITEURL from Pelican settings
            generate_content: Whether to generate new content or use cached
        """
        self.siteurl = siteurl
        self.generate_content = generate_content

    def process_content(self, content: str) -> str:
        """
        Process content: find dialogue_practice tags and convert to HTML.

        Args:
            content: The HTML/markdown content

        Returns:
            Processed content with dialogue_practice tags replaced by interactive buttons
        """
        if not content or "<dialogue_practice>" not in content.lower():
            return content

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        # Find all dialogue_practice tags (case-insensitive)
        dialogue_tags = soup.find_all("dialogue_practice")

        if not dialogue_tags:
            # Try with underscore variant
            dialogue_tags = soup.find_all("dialogue-practice")

        if not dialogue_tags:
            return content

        _log.info(f"Found {len(dialogue_tags)} dialogue_practice tag(s)")

        # Process each tag
        for tag in dialogue_tags:
            instructions = tag.get_text().strip()

            if not instructions:
                _log.warning("Empty dialogue_practice tag found, skipping")
                continue

            # Generate unique ID for this dialogue section
            tag_id = hashlib.md5(instructions.encode()).hexdigest()[:8]

            # Create the replacement HTML
            html_string = self.generate_dialogue_html(instructions, tag_id)

            # Parse the new HTML and replace the tag
            new_element = BeautifulSoup(html_string, "html.parser")
            tag.replace_with(new_element)

            _log.debug(f"Replaced dialogue_practice tag with ID: dialogue-{tag_id}")

        # Convert back to string
        return str(soup)

    def generate_dialogue_html(self, instructions: str, tag_id: str) -> str:
        """
        Generate HTML for a dialogue practice section.

        Args:
            instructions: The instructions text for the AI conversation
            tag_id: Unique identifier for this dialogue section

        Returns:
            HTML string for the dialogue practice section
        """
        # Escape instructions for JSON
        instructions_json = json.dumps({"instructions": instructions})

        html = f'''<div class="dialogue-practice-section">
    <div class="dialogue-practice-header">
        <h3>Conversation Practice</h3>
        <button class="dialogue-practice-button" type="button" data-state="idle" data-instructions-id="dialogue-{tag_id}">
            Start Practice
        </button>
    </div>
    <div class="dialogue-practice-feedback" style="display: none;"></div>
    <script type="application/json" id="dialogue-{tag_id}">
{instructions_json}
    </script>
</div>'''

        return html


def get_processor(siteurl: str, generate_content: bool):
    """
    Get or create the global processor instance.

    Args:
        siteurl: The SITEURL from Pelican settings
        generate_content: Whether to generate new content

    Returns:
        DialoguePracticeProcessor instance
    """
    global _processor, _current_siteurl

    if _processor is None or _current_siteurl != siteurl:
        _processor = DialoguePracticeProcessor(siteurl, generate_content)
        _current_siteurl = siteurl

    return _processor
