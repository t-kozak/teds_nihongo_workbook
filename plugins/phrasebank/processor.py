"""
Phrasebank Processor

Handles parsing of phrasebank sections and generation of semantic HTML
using definition lists (dl/dt/dd) for Japanese phrases with translations.
"""

import re


class PhrasebankProcessor:
    """Processes phrasebank sections in Pelican content."""

    # Pattern to match phrasebank sections
    PHRASEBANK_PATTERN = re.compile(
        r"<phrasebank>(.*?)</phrasebank>", re.DOTALL | re.IGNORECASE
    )

    # Pattern to match individual phrase entries
    # Format: ${phrase in jp}:${en translation} (${context})
    PHRASE_ENTRY_PATTERN = re.compile(
        r"^\s*-\s*(.+?):\s*(.+?)\s*\((.+?)\)\s*$", re.MULTILINE
    )

    def __init__(self, siteurl: str = ""):
        """Initialize the processor.

        Args:
            siteurl: The SITEURL from Pelican settings for generating correct paths
        """
        self.siteurl = siteurl

    def extract_phrasebank_sections(
        self, content: str
    ) -> list[tuple[str, list[tuple[str, str, str]]]]:
        """
        Extract all phrasebank sections from content.

        Args:
            content: The markdown content

        Returns:
            List of tuples: (full_match_text, [(phrase_jp, translation_en, context), ...])
        """
        sections = []
        if not content:
            return []

        for match in self.PHRASEBANK_PATTERN.finditer(content):
            full_match = match.group(0)
            phrasebank_content = match.group(1)

            # Parse individual phrase entries
            phrases = []
            for phrase_match in self.PHRASE_ENTRY_PATTERN.finditer(phrasebank_content):
                phrase_jp = phrase_match.group(1).strip()
                translation_en = phrase_match.group(2).strip()
                context = phrase_match.group(3).strip()
                phrases.append((phrase_jp, translation_en, context))

            if phrases:
                sections.append((full_match, phrases))

        return sections

    def generate_phrase_html(
        self, phrase_jp: str, translation_en: str, context: str
    ) -> str:
        """
        Generate HTML for a single phrase using definition list markup.

        Args:
            phrase_jp: The Japanese phrase
            translation_en: The English translation
            context: The context/description

        Returns:
            HTML string for the phrase (dt + 2x dd)
        """
        # Escape HTML special characters
        translation_escaped = self._escape_html(translation_en)
        context_escaped = self._escape_html(context)

        # Wrap Japanese phrase in <tts> tag for audio generation
        # Don't escape the phrase_jp since it will be processed by TTS plugin
        html = f"""    <dt><tts>{phrase_jp}</tts></dt>
    <dd class="translation">{translation_escaped}</dd>
    <dd class="context">{context_escaped}</dd>
"""

        return html

    def generate_phrasebank_section_html(
        self, phrases: list[tuple[str, str, str]]
    ) -> str:
        """
        Generate complete HTML section for all phrases.

        Args:
            phrases: List of (phrase_jp, translation_en, context) tuples

        Returns:
            Complete HTML section with definition list
        """
        # Generate individual phrases
        phrases_html = ""
        for phrase_jp, translation_en, context in phrases:
            phrases_html += self.generate_phrase_html(
                phrase_jp, translation_en, context
            )

        # Complete HTML with dl container
        complete_html = f"""<dl class="phrase-list">
{phrases_html}</dl>
"""

        return complete_html

    def process_content(self, content: str) -> str:
        """
        Process content: extract phrasebank sections and generate HTML.

        This is the main entry point that replaces phrasebank tags with HTML.

        Args:
            content: The markdown content

        Returns:
            Processed content with phrasebank sections replaced by HTML
        """
        sections = self.extract_phrasebank_sections(content)

        if not sections:
            return content

        # Process each section
        for full_match, phrases in sections:
            # Generate HTML
            html = self.generate_phrasebank_section_html(phrases)

            # Replace the phrasebank section with HTML
            content = content.replace(full_match, html)

        return content

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
