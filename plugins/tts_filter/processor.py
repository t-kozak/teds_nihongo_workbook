"""
TTS Processor

Handles parsing of TTS sections, generation of audio files using Google's Gemini TTS API,
and generation of HTML audio elements.
"""

import asyncio
import hashlib
import logging
import re
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, TypedDict, cast

from tts import TTS

_log = logging.getLogger(__name__)


class DialogueSectionData(TypedDict):
    """Type for dialogue section data."""

    full_match: str
    type: str
    dialogue: list[tuple[str, str]]
    text_content: str


class SimpleSectionData(TypedDict):
    """Type for simple (inline/full) section data."""

    full_match: str
    type: str
    text_content: str


class TTSProcessor:
    """Processes TTS sections in Pelican content."""

    # Pattern to match TTS sections with optional attributes
    # Format: <tts type="inline|full|dialogue" voice="voice_name" speakers="speaker1:voice1,speaker2:voice2">text content</tts>
    TTS_PATTERN = re.compile(
        r'<tts(?:\s+type="(inline|full|dialogue)")?(?:\s+voice="([^"]+)")?(?:\s+speakers="([^"]+)")?\s*>(.*?)</tts>',
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(self, siteurl: str = "", dev_mode: bool = False):
        """Initialize the processor with a TTS instance.

        Args:
            siteurl: The SITEURL from Pelican settings for generating correct paths
            dev_mode: If True, skip audio generation and only generate HTML from cached files
        """
        self.siteurl = siteurl
        self.dev_mode = dev_mode
        self.tts = None if dev_mode else TTS()
        # Cache to store generated audio files during processing
        self._audio_cache = {}
        # Base path for audio files
        self.audio_base_path = (
            Path(__file__).parent.parent.parent / "content" / "audio" / "tts"
        )
        # Ensure audio directory exists
        self.audio_base_path.mkdir(parents=True, exist_ok=True)

    def extract_tts_sections(
        self, content: str
    ) -> list[tuple[str, str, str | None, str | None, str]]:
        """
        Extract all TTS sections from content.

        Args:
            content: The markdown content

        Returns:
            List of tuples: (full_match_text, type, voice, speakers, text_content)
            where type defaults to "inline" if not specified
        """
        sections = []
        if not content:
            return []

        for match in self.TTS_PATTERN.finditer(content):
            full_match = match.group(0)
            tts_type = match.group(1) or "inline"  # Default to inline
            voice = match.group(2)  # Can be None
            speakers = match.group(3)  # Can be None
            text_content = match.group(4).strip()

            sections.append((full_match, tts_type, voice, speakers, text_content))

        return sections

    def generate_audio_filename(self, text: str) -> str:
        """
        Generate a unique filename for the audio based on text content.

        Args:
            text: The text content to generate audio for

        Returns:
            Filename in format: {md5_hash}.aac
        """
        # Create MD5 hash of the text content
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        return f"{text_hash}.aac"

    async def generate_audio(self, text: str, voice: str | None = None) -> Path:
        """
        Generate audio file for the given text.

        Args:
            text: The text to convert to speech
            voice: Optional voice name to use for TTS

        Returns:
            Path to the generated audio file
        """
        filename = self.generate_audio_filename(text)
        output_path = self.audio_base_path / filename

        # Check cache first
        cache_key = (text, voice)
        if cache_key in self._audio_cache:
            return self._audio_cache[cache_key]

        # Check if file already exists on disk
        if output_path.exists():
            _log.info(f"Using cached audio file: {filename}")
            self._audio_cache[cache_key] = output_path
            return output_path

        # In dev mode, return path even if file doesn't exist
        # (HTML generation will skip if file is missing)
        if self.dev_mode:
            self._audio_cache[cache_key] = output_path
            return output_path

        # Generate the audio file
        _log.info(f"Generating audio for: {text[:50]}{'...' if len(text) > 50 else ''}")
        try:
            assert self.tts is not None
            if voice:
                await self.tts.generate(text, output_path, voice=voice)
            else:
                await self.tts.generate(text, output_path)

            self._audio_cache[cache_key] = output_path
            return output_path
        except Exception:
            _log.exception(f"Error generating audio for '{text[:50]}...'")

            return output_path

    def parse_speakers_config(self, speakers_str: str) -> dict[str, str]:
        """
        Parse the speakers attribute string into a speaker-to-voice mapping.

        Args:
            speakers_str: String in format "speaker1:voice1,speaker2:voice2,..."

        Returns:
            Dictionary mapping speaker names to voice names

        Raises:
            ValueError: If the format is invalid
        """
        speaker_cfg = {}
        pairs = speakers_str.split(",")

        for pair in pairs:
            pair = pair.strip()
            if ":" not in pair:
                raise ValueError(
                    f"Invalid speaker config format: '{pair}'. Expected 'speaker:voice'"
                )

            speaker, voice = pair.split(":", 1)
            speaker = speaker.strip()
            voice = voice.strip()

            if not speaker or not voice:
                raise ValueError(
                    f"Invalid speaker config: '{pair}'. Both speaker and voice must be non-empty"
                )

            speaker_cfg[speaker] = voice

        return speaker_cfg

    def parse_dialogue_content(self, content: str) -> list[tuple[str, str]]:
        """
        Parse dialogue content in format "- speaker: text" into list of tuples.

        Args:
            content: Dialogue content with each line as "- speaker: text"
                     (supports both ASCII ':' and full-width '：' colons)

        Returns:
            List of (speaker, text) tuples

        Raises:
            ValueError: If the format is invalid
        """
        # Pattern matches: optional whitespace, dash, whitespace, speaker name, colon (ASCII or full-width), text
        # [^:：] matches any character except ASCII colon or full-width colon
        # [:：] matches either ASCII colon or full-width colon
        dialogue_pattern = re.compile(r"^\s*-\s*([^:：]+)[:：]\s*(.+)$", re.MULTILINE)

        dialogue = []
        for match in dialogue_pattern.finditer(content):
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            dialogue.append((speaker, text))

        if not dialogue:
            raise ValueError(
                "No valid dialogue lines found. Expected format: '- speaker: text' or '- speaker：text'"
            )

        return dialogue

    def validate_dialogue_speakers(
        self, dialogue: list[tuple[str, str]], speaker_cfg: dict[str, str]
    ) -> None:
        """
        Validate that all speakers in the dialogue have voice configurations.

        Args:
            dialogue: List of (speaker, text) tuples
            speaker_cfg: Dictionary mapping speaker names to voice names

        Raises:
            ValueError: If any speaker lacks a voice configuration
        """
        dialogue_speakers = {speaker for speaker, _ in dialogue}
        configured_speakers = set(speaker_cfg.keys())

        missing_speakers = dialogue_speakers - configured_speakers
        if missing_speakers:
            raise ValueError(
                f"Missing voice configuration for speakers: {', '.join(sorted(missing_speakers))}"
            )

    async def generate_dialogue_audio(
        self, dialogue: list[tuple[str, str]], speaker_cfg: dict[str, str]
    ) -> Path:
        """
        Generate audio file for a dialogue.

        Args:
            dialogue: List of (speaker, text) tuples
            speaker_cfg: Dictionary mapping speaker names to voice names

        Returns:
            Path to the generated audio file
        """
        # Create a unique identifier for this dialogue
        dialogue_text = "\n".join(f"{speaker}: {text}" for speaker, text in dialogue)
        filename = self.generate_audio_filename(dialogue_text)
        output_path = self.audio_base_path / filename

        # Check cache
        cache_key = (dialogue_text, tuple(sorted(speaker_cfg.items())))
        if cache_key in self._audio_cache:
            return self._audio_cache[cache_key]

        # Check if file already exists on disk
        if output_path.exists():
            _log.info(f"Using cached dialogue audio file: {filename}")
            self._audio_cache[cache_key] = output_path
            return output_path

        # In dev mode, return path even if file doesn't exist
        if self.dev_mode:
            self._audio_cache[cache_key] = output_path
            return output_path

        # Generate the audio file
        _log.info(f"Generating dialogue audio with {len(dialogue)} turns...")
        try:
            assert self.tts is not None
            await self.tts.generate_dialogue(speaker_cfg, dialogue, output_path)
            self._audio_cache[cache_key] = output_path
            return output_path
        except Exception:
            _log.exception("Error generating dialogue audio")

            return output_path

    def generate_inline_html(self, text: str, audio_filename: str) -> str:
        """
        Generate inline HTML with hidden audio and speaker icon link.

        Args:
            text: The original text content
            audio_filename: The audio filename (not full path)

        Returns:
            HTML string with text followed by audio element and speaker icon
        """
        # Check if audio file exists
        audio_file_path = self.audio_base_path / audio_filename
        if not audio_file_path.exists():
            _log.info(
                f"Warning: Audio file not found for inline TTS - skipping audio button: {audio_filename}"
            )
            return text

        audio_path = f"{self.siteurl}/audio/tts/{audio_filename}"
        speaker_icon_path = f"{self.siteurl}/images/audio-speaker.svg"

        # Don't escape the text - it's still markdown at this point and will be processed later
        html = f"""<audio class="tts-audio" style="display: none;">
    <source src="{audio_path}" type="audio/aac">
    Your browser does not support the audio element.
</audio>
<a href="#" class="tts-audio-btn" style="text-decoration: none; border: none;" aria-label="Play pronunciation" onclick="event.preventDefault(); this.previousElementSibling.play();">
    <img src="{speaker_icon_path}" alt="Play" width="16" height="16" style="vertical-align: middle;">
</a>{text}"""

        return html

    def generate_full_html(self, text: str, audio_filename: str) -> str:
        """
        Generate full HTML with text and audio player with controls.

        Args:
            text: The original text content
            audio_filename: The audio filename (not full path)

        Returns:
            HTML string with text followed by audio element with controls
        """
        # Check if audio file exists
        audio_file_path = self.audio_base_path / audio_filename
        if not audio_file_path.exists():
            _log.info(
                f"Warning: Audio file not found for full TTS - skipping audio controls: {audio_filename}"
            )
            return text

        audio_path = f"{self.siteurl}/audio/tts/{audio_filename}"

        # Don't escape the text - it's still markdown at this point and will be processed later
        html = f"""{text}
<div style="margin-top: 1em;">
    <audio controls class="tts-audio-full">
        <source src="{audio_path}" type="audio/aac">
        Your browser does not support the audio element.
    </audio>
</div>"""

        return html

    def generate_dialogue_html(
        self, dialogue: list[tuple[str, str]], audio_filename: str
    ) -> str:
        """
        Generate HTML for dialogue using definition list structure with audio player.

        Args:
            dialogue: List of (speaker, text) tuples
            audio_filename: The audio filename (not full path)

        Returns:
            HTML string with formatted dialogue as <dl> and audio player
        """
        # Check if audio file exists
        audio_file_path = self.audio_base_path / audio_filename
        if not audio_file_path.exists():
            _log.info(
                f"Warning: Audio file not found for dialogue TTS - skipping audio controls: {audio_filename}"
            )
            # Return plain dialogue text if audio is missing
            dialogue_lines = [f"- {speaker}: {text}" for speaker, text in dialogue]
            return "\n".join(dialogue_lines)

        audio_path = f"{self.siteurl}/audio/tts/{audio_filename}"

        # Build definition list HTML structure
        dl_items = []
        for speaker, text in dialogue:
            # Don't escape - the text will be processed by other Pelican plugins (like furigana)
            dl_items.append(f"    <dt>{speaker}</dt>")
            dl_items.append(f"    <dd>{text}</dd>")

        dialogue_html = "\n".join(dl_items)

        html = f"""<dl class="dialogue">
{dialogue_html}
</dl>
<div class="dialogue-audio">
    <audio controls class="tts-audio-dialogue">
        <source src="{audio_path}" type="audio/aac">
        Your browser does not support the audio element.
    </audio>
</div>"""

        return html

    async def process_content(self, content: str) -> str:
        """
        Process content: extract TTS sections, generate audio, and generate HTML.

        This is the main entry point that combines all processing steps.
        Audio generation is performed concurrently for all sections to improve performance.

        Args:
            content: The markdown content

        Returns:
            Processed content with TTS sections replaced by HTML audio elements
        """
        sections = self.extract_tts_sections(content)

        if not sections:
            return content

        # Prepare all sections and validate them first
        tasks: list[Coroutine[Any, Any, Path]] = []
        section_data: list[DialogueSectionData | SimpleSectionData] = []

        for full_match, tts_type, voice, speakers, text_content in sections:
            try:
                if tts_type == "dialogue":
                    # Handle dialogue type
                    if not speakers:
                        _log.info(
                            f"Warning: Dialogue type requires 'speakers' attribute - skipping: {full_match[:50]}..."
                        )
                        continue

                    # Parse speaker configuration
                    speaker_cfg = self.parse_speakers_config(speakers)

                    # Parse dialogue content
                    dialogue = self.parse_dialogue_content(text_content)

                    # Validate speakers
                    self.validate_dialogue_speakers(dialogue, speaker_cfg)

                    # Create task for dialogue audio generation
                    task = self.generate_dialogue_audio(dialogue, speaker_cfg)
                    tasks.append(task)
                    section_data.append(
                        {
                            "full_match": full_match,
                            "type": tts_type,
                            "dialogue": dialogue,
                            "text_content": text_content,
                        }
                    )
                else:
                    # Handle inline and full types
                    task = self.generate_audio(text_content, voice)
                    tasks.append(task)
                    section_data.append(
                        {
                            "full_match": full_match,
                            "type": tts_type,
                            "text_content": text_content,
                        }
                    )

            except ValueError as e:
                _log.info(f"Error processing TTS section: {e}")
                _log.info(f"Skipping section: {full_match[:100]}...")
                continue

        # Generate all audio files concurrently
        if tasks:
            _log.info(f"Generating audio for {len(tasks)} TTS sections concurrently...")
            audio_paths = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and generate HTML
            for i, (audio_result, section_info) in enumerate(
                zip(audio_paths, section_data)
            ):
                try:
                    # Check if audio generation failed
                    if isinstance(audio_result, Exception):
                        _log.info(f"Error generating audio for section: {audio_result}")
                        continue

                    # Type narrowing: audio_result is Path after exception check
                    audio_path = cast(Path, audio_result)
                    audio_filename = audio_path.name
                    full_match = section_info["full_match"]
                    tts_type = section_info["type"]

                    # Generate HTML based on type
                    if tts_type == "dialogue":
                        # Type narrowing: section_info is DialogueSectionData
                        dialogue_section = cast(DialogueSectionData, section_info)
                        dialogue = dialogue_section["dialogue"]
                        html = self.generate_dialogue_html(dialogue, audio_filename)
                    elif tts_type == "full":
                        text_content = section_info["text_content"]
                        html = self.generate_full_html(text_content, audio_filename)
                    else:  # inline (default)
                        text_content = section_info["text_content"]
                        html = self.generate_inline_html(text_content, audio_filename)

                    # Replace the TTS section with HTML
                    content = content.replace(full_match, html)

                except Exception:
                    _log.exception("Error processing TTS section result")
                    continue

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
