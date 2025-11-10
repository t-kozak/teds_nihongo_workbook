import mimetypes
import re
import struct
import tempfile
from pathlib import Path

import fugashi
from ffmpeg import FFmpeg
from google import genai  # type: ignore
from google.genai import types

from tools import load_google_api_key


class TTS:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or "gemini-2.5-flash-preview-tts"
        self.client = genai.Client(
            api_key=load_google_api_key(),
        )
        self.tagger = fugashi.Tagger()  # type: ignore

    def generate(self, content: str, output: Path):
        """Generate TTS audio and save as AAC format.

        Converts any kanji in the input text to hiragana before generating speech.

        Args:
            content: The text to convert to speech
            output: Path where the AAC audio file should be saved
        """
        # Convert kanji to hiragana before generating speech
        hiragana_content = self._kanji_to_hiragana(content)

        print(f"Generating TTS for hiragana content: {hiragana_content}")
        # Generate audio using Gemini TTS
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=hiragana_content),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=[
                "audio",
            ],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
                )
            ),
        )

        # Collect all audio chunks
        audio_data = None
        mime_type = None

        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            if (
                chunk.candidates[0].content.parts[0].inline_data
                and chunk.candidates[0].content.parts[0].inline_data.data
            ):
                inline_data = chunk.candidates[0].content.parts[0].inline_data
                audio_data = inline_data.data
                mime_type = inline_data.mime_type
                break

        if audio_data is None or mime_type is None:
            raise RuntimeError("No audio data generated")

        # Convert to WAV format first if needed
        file_extension = mimetypes.guess_extension(mime_type)
        if file_extension is None:
            wav_data = self._convert_to_wav(audio_data, mime_type)
        else:
            wav_data = audio_data

        # Write WAV to temporary file and convert to AAC
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav.write(wav_data)
            temp_wav_path = temp_wav.name

        try:
            # Convert WAV to AAC using ffmpeg
            ffmpeg_converter = (
                FFmpeg()
                .option("y")
                .input(temp_wav_path)
                .output(str(output), {"codec:a": "aac", "b:a": "128k"})
            )
            ffmpeg_converter.execute()
        finally:
            # Clean up temporary WAV file
            Path(temp_wav_path).unlink()

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Generates a WAV file header for the given audio data and parameters.

        Args:
            audio_data: The raw audio data as a bytes object.
            mime_type: Mime type of the audio data.

        Returns:
            A bytes object representing the WAV file header.
        """
        parameters = self._parse_audio_mime_type(mime_type)
        bits_per_sample = parameters["bits_per_sample"]
        sample_rate = parameters["rate"]
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",  # ChunkID
            chunk_size,  # ChunkSize (total file size - 8 bytes)
            b"WAVE",  # Format
            b"fmt ",  # Subchunk1ID
            16,  # Subchunk1Size (16 for PCM)
            1,  # AudioFormat (1 for PCM)
            num_channels,  # NumChannels
            sample_rate,  # SampleRate
            byte_rate,  # ByteRate
            block_align,  # BlockAlign
            bits_per_sample,  # BitsPerSample
            b"data",  # Subchunk2ID
            data_size,  # Subchunk2Size (size of audio data)
        )
        return header + audio_data

    def _parse_audio_mime_type(self, mime_type: str) -> dict[str, int]:
        """Parses bits per sample and rate from an audio MIME type string.

        Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

        Args:
            mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

        Returns:
            A dictionary with "bits_per_sample" and "rate" keys.
        """
        bits_per_sample = 16
        rate = 24000

        # Extract rate from parameters
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate_str = param.split("=", 1)[1]
                    rate = int(rate_str)
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass

        return {"bits_per_sample": bits_per_sample, "rate": rate}

    def _kanji_to_hiragana(self, text: str) -> str:
        """Convert kanji in text to hiragana.

        Args:
            text: Text containing kanji characters

        Returns:
            Text with kanji converted to hiragana readings
        """
        if not text.strip():
            return text

        # Pattern to match Japanese text (hiragana, katakana, kanji, Japanese punctuation)
        japanese_pattern = re.compile(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]+"
        )

        output = []
        last_end = 0

        for match in japanese_pattern.finditer(text):
            # Add any non-Japanese text before this match
            if match.start() > last_end:
                output.append(text[last_end : match.start()])

            # Process the Japanese segment
            japanese_segment = match.group()
            output.append(self._process_japanese_segment(japanese_segment))

            last_end = match.end()

        # Add any remaining non-Japanese text
        if last_end < len(text):
            output.append(text[last_end:])

        return "".join(output)

    def _process_japanese_segment(self, text: str) -> str:
        """Process a Japanese text segment to convert kanji to hiragana.

        Args:
            text: Japanese text string (hiragana, katakana, kanji)

        Returns:
            Text with kanji converted to hiragana readings
        """
        # Parse text with morphological analyzer
        words = self.tagger(text)

        output = []
        for word in words:
            orig = word.surface  # Original text

            # Get katakana reading and convert to hiragana
            kana = word.feature.kana if hasattr(word.feature, "kana") else None

            if kana:
                hira = self._katakana_to_hiragana(kana)
            else:
                # No reading available, use original text
                hira = orig

            # Check if this segment contains kanji
            if self._contains_kanji(orig):
                # Use hiragana reading
                output.append(hira)
            else:
                # No kanji - preserve as-is
                output.append(orig)

        return "".join(output)

    def _katakana_to_hiragana(self, text: str) -> str:
        """Convert katakana characters to hiragana.

        Args:
            text: String containing katakana characters

        Returns:
            String with katakana converted to hiragana
        """
        hiragana = []
        for char in text:
            code = ord(char)
            # Katakana range: U+30A0 to U+30FF
            # Hiragana range: U+3040 to U+309F
            # Offset is 0x60 (96)
            if 0x30A0 <= code <= 0x30FF:
                hiragana.append(chr(code - 0x60))
            else:
                hiragana.append(char)
        return "".join(hiragana)

    def _contains_kanji(self, text: str) -> bool:
        """Check if text contains any kanji characters.

        Kanji Unicode ranges:
        - CJK Unified Ideographs: U+4E00 to U+9FFF
        - CJK Unified Ideographs Extension A: U+3400 to U+4DBF

        Args:
            text: String to check

        Returns:
            True if text contains kanji, False otherwise
        """
        kanji_pattern = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")
        return bool(kanji_pattern.search(text))


if __name__ == "__main__":
    tts = TTS()
    tts.generate("今日", Path("output.aac"))
