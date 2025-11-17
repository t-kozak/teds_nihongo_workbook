"""Japanese text processor with LLM-based word segmentation, translation, and furigana."""

import asyncio
import html as html_module
import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import List, Optional

import marvin
from bs4 import BeautifulSoup
from markupsafe import Markup
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from tools import load_google_api_key

from .cache import get_cache

_log = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = 30  # Number of Japanese text chunks to process concurrently
MAX_RETRIES = 1  # Number of retry attempts for failed LLM calls

# Cache configuration (can be overridden via environment variables)
CACHE_ENABLED = True  # Set to False to disable caching
CACHE_TTL = 86400 * 30  # 30 days in seconds

# Japanese punctuation characters (single-char segments to skip)
# These are useful as context in sentences, but shouldn't be processed alone
SKIP_SINGLE_CHARS = set(
    "　、。〃〄々〆〇〈〉《》「」『』【】〒〓〔〕〖〗〘〙〚〛〜〝〞〟"
    "〠〡〢〣〤〥〦〧〨〩〰〱〲〳〴〵〶〷〸〹〺〻〼〽〾〿・"
)

CACHE_VERSION = "v6"


@dataclass
class JapaneseWordSpan:
    text: str
    eng: str
    furigana: str | None = None


@dataclass
class JapaneseWordSpans:
    spans: list[JapaneseWordSpan]


def _create_agent(instructions: str) -> marvin.Agent:
    """Create the default Google Gemini agent."""
    google_api_key = load_google_api_key()
    return marvin.Agent(
        instructions="You are a Japanese language expert that converts Japanese text into semantically annotated HTML.",
        model=GoogleModel(
            model_name="models/gemini-flash-latest",
            provider=GoogleProvider(api_key=google_api_key),
        ),
    )


def _should_skip_segment(text: str) -> bool:
    """
    Check if a text segment should be skipped (not sent to LLM).

    Skips single-character punctuation marks that don't need translation.
    These characters are still useful as context in longer segments.

    Args:
        text: Text segment to check

    Returns:
        True if segment should be skipped, False otherwise
    """
    # Skip single-character punctuation
    if len(text) == 1 and text in SKIP_SINGLE_CHARS:
        return True
    return False


class JapaneseTextProcessor:
    """
    Process Japanese text using LLM to add word boundaries, translations, and furigana.

    This processor:
    1. Identifies continuous Japanese text segments using regex
    2. Processes segments in async batches for performance
    3. Uses Marvin Agent to convert text to semantically annotated HTML spans
    4. Caches LLM responses in Redis to reduce API costs
    """

    def __init__(self, cache_enabled: bool = CACHE_ENABLED, cache_ttl: int = CACHE_TTL):
        """
        Initialize the processor.

        Args:
            cache_enabled: Whether to enable Redis caching
            cache_ttl: Time-to-live for cache entries in seconds
        """
        # Pattern to match continuous Japanese text (hiragana, katakana, kanji, Japanese punctuation)
        self.japanese_pattern = re.compile(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]+"
        )

        # Initialize cache
        self.cache = get_cache(key_prefix=CACHE_VERSION)

    def process_content(self, html_content: str) -> str:
        """
        Process HTML content to add Japanese word annotations.

        Args:
            html_content: HTML string containing Japanese text

        Returns:
            HTML string with Japanese words wrapped in annotated spans
        """
        _log.info(f"Processing html:\n\n{html_content}")
        if not html_content:
            _log.info(" Empty content, skipping")
            return html_content

        _log.info(f"Processing content (length: {len(str(html_content))} chars)")

        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(str(html_content), "html.parser")

        # Get all text nodes
        text_nodes = soup.find_all(string=True)

        # Process text nodes in batches
        try:
            asyncio.run(self._process_text_nodes_in_batches(text_nodes))
        except Exception as e:
            _log.info(f"Error during async processing: {e}")
            # Return original content if processing fails
            return html_content

        result = str(soup)
        _log.info(" Processing complete")
        return Markup(result)

    async def _process_text_nodes_in_batches(self, text_nodes: List) -> None:
        """
        Process text nodes in async batches.

        Args:
            text_nodes: List of BeautifulSoup text nodes to process
        """
        # Process in batches
        for i in range(0, len(text_nodes), BATCH_SIZE):
            batch = text_nodes[i : i + BATCH_SIZE]
            _log.info(
                f"Processing batch {i // BATCH_SIZE + 1} ({len(batch)} text nodes)"
            )

            # Process batch concurrently
            await asyncio.gather(
                *[self._process_text_node(node) for node in batch],
                return_exceptions=True,
            )

    async def _process_text_node(self, text_node) -> None:
        """
        Process a single text node, replacing Japanese text with annotated spans.

        Args:
            text_node: BeautifulSoup text node to process
        """
        # Skip text inside ignored tags
        if text_node.parent is not None and text_node.parent.name in [
            "script",
            "style",
            "wordbank",
        ]:
            return

        # Check if text contains Japanese characters
        original_text = str(text_node)
        matches = []
        japanese_segments = []

        for match in self.japanese_pattern.finditer(original_text):
            matched_text = match.group()
            # Skip single-character punctuation
            if not _should_skip_segment(matched_text):
                japanese_segments.append(matched_text)
                matches.append((match.start(), match.end(), matched_text))

        # If no Japanese text, skip
        if not matches:
            return

        # Process all Japanese segments from this text node
        processed_segments = []
        for segment in japanese_segments:
            response = await self._call_llm_for_segment(segment)
            processed = self._extract_html_from_response(
                response or JapaneseWordSpans([]), segment
            )
            processed_segments.append(processed)

        # Build the new text content by replacing Japanese segments
        result_parts = []
        last_end = 0
        processed_idx = 0

        for start, end, _ in matches:
            # Add text before this match
            result_parts.append(original_text[last_end:start])
            # Add processed version
            result_parts.append(processed_segments[processed_idx])
            processed_idx += 1
            last_end = end

        # Add remaining text after last match
        result_parts.append(original_text[last_end:])

        # Replace the text node with the processed version
        new_content = BeautifulSoup("".join(result_parts), "html.parser")
        text_node.replace_with(new_content)

    async def _call_llm_for_segment(self, text: str) -> Optional[JapaneseWordSpans]:
        """
        Call LLM to process a Japanese text segment (with caching).

        This method is separated to allow caching of the raw LLM response
        before HTML conversion, so that HTML generation logic changes don't
        require cache invalidation.

        Args:
            text: Japanese text string to process

        Returns:
            JapaneseWordSpans object from LLM, or None if call failed
        """
        # Check cache first (cache stores JSON serialized response)
        cached_json = self.cache.get(text)
        if cached_json is not None:
            try:
                # Deserialize from JSON
                data = json.loads(cached_json)
                # Reconstruct JapaneseWordSpans from dict
                spans = [JapaneseWordSpan(**item) for item in data.get("spans", [])]
                return JapaneseWordSpans(spans=spans)
            except Exception as e:
                _log.info(f"Error deserializing cached response: {e}")
                # Fall through to LLM call

        # Cache miss - call LLM
        try:
            prompt = self._build_llm_prompt(text)
            agent = _create_agent(prompt)

            _log.info(f"Processing text: {text}")
            response = await agent.run_async(
                prompt, result_type=JapaneseWordSpans, handlers=[]
            )
            _log.info(f"{text} -> {response}")

            # Serialize and cache the response using asdict()
            response_dict = asdict(response)
            self.cache.set(text, json.dumps(response_dict))

            return response

        except Exception as e:
            _log.info(f"LLM call failed: {e}")
            return None

    def _build_llm_prompt(self, text: str) -> str:
        """
        Build the LLM prompt for processing Japanese text.

        Args:
            text: Japanese text to process

        Returns:
            Prompt string for the LLM
        """
        return f"""Your task is to identify individual Japanese words in the text and provide translations and readings.

IMPORTANT INSTRUCTIONS:
1. Only identify meaningful Japanese words (nouns, verbs, adjectives, particles, etc.)
2. DO NOT include any punctuation marks (。、！？quotes, etc.) in your word list
3. For each word, provide a JapaneseWordSpan object with:
   - text: The Japanese word itself (exactly as it appears in the original text)
   - eng: The English meaning of the word in the context of the sentence or a description of a function for particles
   - furigana: The reading in hiragana, ONLY if the word contains kanji.
4. Return the words in the order they appear in the original text
5. Important! The text must exactly match the word in the input text.

Process the following text:
{text}"""

    def _extract_html_from_response(
        self, response: JapaneseWordSpans, original_text: str
    ) -> str:
        """
        Convert structured JapaneseWordSpans response to HTML by algorithmically
        matching words back to the original text.

        Args:
            response: JapaneseWordSpans object from Marvin agent
            original_text: The original Japanese text segment

        Returns:
            HTML string with annotated word spans, or None if conversion failed
        """
        _log.info("\n\n\n.")

        if not response.spans:
            _log.info("No spans provided by LLM, returning original text")
            return original_text
        try:
            _log.info(f"Mapping {original_text}, via:")
            for span in response.spans:
                _log.info(f"{span.text} ({span.furigana}) -> {span.eng}")

            # Start with the original text
            result = original_text

            # Track positions to avoid overlapping replacements
            # We'll collect all replacements and apply them in reverse order
            # to avoid index shifting issues
            replacements = []

            # Current search position in the text
            search_pos = 0

            for span in response.spans:
                # Find the word in the original text starting from search_pos
                word_pos = result.find(span.text, search_pos)

                if word_pos == -1:
                    _log.info(
                        f"Warning: Could not find word '{span.text}' in text '{original_text}'"
                    )
                    continue

                # Validate furigana - skip if it's the same as the text
                valid_furigana = None
                if span.furigana and span.furigana.strip() != span.text.strip():
                    valid_furigana = span.furigana.strip()

                # Build the span content
                if valid_furigana:
                    # Use ruby tags for words with furigana
                    inner_html = (
                        f"<ruby>{html_module.escape(span.text)}"
                        f"<rt>{html_module.escape(valid_furigana)}</rt></ruby>"
                    )
                else:
                    # Plain text for words without furigana
                    inner_html = html_module.escape(span.text)

                # Build the complete span element with translation
                translation_escaped = html_module.escape(span.eng, quote=True)
                replacement_html = f'<span class="jp-word" data-en-translation="{translation_escaped}">{inner_html}</span>'

                # Store replacement info (position, length, replacement text)
                replacements.append((word_pos, len(span.text), replacement_html))

                # Move search position forward to after this word
                search_pos = word_pos + len(span.text)

            # Apply replacements in reverse order to avoid index shifting
            for pos, length, replacement in reversed(replacements):
                result = result[:pos] + replacement + result[pos + length :]

            _log.info(f"Converted {original_text} -> {result}")
            return result

        except Exception:
            _log.exception("Error converting response to HTML")
            return original_text


# Global processor instance
_processor = None


def get_processor(
    cache_enabled: bool = CACHE_ENABLED,
    cache_ttl: int = CACHE_TTL,
) -> JapaneseTextProcessor:
    """
    Get or create the global processor instance.

    Args:
        cache_enabled: Whether to enable Redis caching
        cache_ttl: Time-to-live for cache entries in seconds

    Returns:
        JapaneseTextProcessor instance
    """
    global _processor
    if _processor is None:
        _processor = JapaneseTextProcessor(
            cache_enabled=cache_enabled,
            cache_ttl=cache_ttl,
        )
    return _processor
