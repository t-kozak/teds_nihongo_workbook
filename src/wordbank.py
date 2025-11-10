import json
from dataclasses import asdict, dataclass
from pathlib import Path

import marvin
from google import genai  # type: ignore
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider


@dataclass
class WordbankWordDetails:
    en_translation: str
    word: str
    language_code: str
    examples: list[str]
    description: str
    image_description: str
    image_file: str | None = None


# Prompt template for generating flashcard details
FLASHCARD_GENERATION_PROMPT = """You are creating flashcard materials for language learners.

Given the following information about a word:
- Language: Japanese
- Word: {word}
- English translation: {en_translation}
- Context/Description: {description}

Generate complete flashcard details with the following requirements:

1. **Description**: The meaning focuses on the specific sense indicated by the English translation and context. If the provided description is insufficient or unclear, expand it to be more complete and helpful for learners. The description should clearly explain this particular meaning of the word.

2. **Examples**: Generate 2-3 natural example sentences that demonstrate how this word is used in this specific meaning. The examples should:
   - Be realistic and practical for learners
   - Show the word in different contexts
   - Be at an appropriate difficulty level for intermediate learners
   - Use the word in its original language (not translated)

3. **Image Description**: Create a description of a scene that would help learners memorize this specific meaning of the word. This description will be used to generate an image using AI image diffusion systems. The description should:
   - Focus on the essence and meaning rather than artistic style
   - Describe a clear, memorable scene that represents the concept
   - Be concrete and visual
   - Help distinguish this meaning from other meanings of the word
   - Be detailed enough for image generation (2-4 sentences)
   - Avoid style instructions (like "photorealistic" or "cartoon") - focus only on content
   - If the word is noun, minimise the amount of other objects in the description not to dillute the message

Remember: This is for a flashcard learning system. The word + English translation + description together represent ONE specific meaning, not all possible meanings of the word.

Provide the complete details as a structured response."""


def _load_google_api_key() -> str:
    """Load Google AI Studio API key from .env file."""
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "GOOGLE_AI_STUDIO_KEY":
                        return value.strip()

    raise ValueError("GOOGLE_AI_STUDIO_KEY not found in .env file")


def _create_default_agent() -> marvin.Agent:
    """Create the default Google Gemini agent."""
    google_api_key = _load_google_api_key()
    return marvin.Agent(
        model=GoogleModel(
            model_name="gemini-2.5-pro", provider=GoogleProvider(api_key=google_api_key)
        )
    )


class WordBank:
    """
    Manages a wordbank for language learning flashcards.

    The wordbank stores word details in a JSONL file with in-memory caching
    and uses an LLM agent to generate complete flashcard data from minimal input.
    """

    def __init__(
        self,
        data_path: str | None = None,
        agent: marvin.Agent | None = None,
    ):
        """
        Initialize the WordBank.

        Args:
            data_path: Path to the JSONL file. If None, uses default path.
            agent: Marvin agent for LLM operations. If None, uses default Gemini agent.
        """
        if data_path is None:
            self.data_path = (
                Path(__file__).parent / "data" / "wordbank.jsonl"
            ).absolute()
        else:
            self.data_path = Path(data_path).absolute()

        self.agent = agent if agent is not None else _create_default_agent()
        self.imagen = genai.Client(api_key=_load_google_api_key())
        self._cache: dict[tuple[str, str], WordbankWordDetails] | None = None

    def get_all(self) -> list["WordbankWordDetails"]:
        data = self._load()
        return list(data.values())

    def contains(self, word: str, en_translation: str) -> bool:
        """
        Check if a word-translation pair exists in the wordbank.

        Args:
            word: The word in the target language
            en_translation: The English translation

        Returns:
            True if the pair exists, False otherwise
        """
        wordbank = self._load()
        return (word, en_translation) in wordbank

    def get(self, word: str, en_translation: str) -> WordbankWordDetails | None:
        """
        Query wordbank for a specific word-translation pair.

        Args:
            word: The word in the target language
            en_translation: The English translation

        Returns:
            WordbankWordDetails if found, None otherwise
        """
        wordbank = self._load()
        return wordbank.get((word, en_translation))

    def upsert(self, details: WordbankWordDetails) -> None:
        """
        Insert or update word details in the wordbank.

        Args:
            details: The word details to upsert
        """
        wordbank = self._load()
        key = (details.word, details.en_translation)
        wordbank[key] = details
        self._save()

    def _generate_word_details(
        self, word: str, en_translation: str, description: str
    ) -> WordbankWordDetails:
        """
        Generate or retrieve word details, using cached data when available.

        Checks if the word already exists in the database with complete details.
        If so, returns the cached data. Otherwise, generates new details using LLM.

        Args:
            word: The word in the target language
            en_translation: The English translation
            description: Context or description to narrow down the meaning

        Returns:
            Complete WordbankWordDetails object
        """
        # Check if we already have this word in the database
        existing = self.get(word, en_translation)

        # If we have existing data with an image description, use it
        if existing and existing.image_description:
            print(f"Found existing data for '{word}' - skipping LLM generation")
            return existing

        # Generate new data using LLM
        print(f"Generating new data for '{word}' using LLM")
        prompt = FLASHCARD_GENERATION_PROMPT.format(
            word=word, en_translation=en_translation, description=description
        )

        # Use the agent to generate the structured output
        result = self.agent.run(
            prompt,
            result_type=WordbankWordDetails,
        )

        print(f"Got result from agent: {result}")
        # Ensure the word and en_translation match the input
        result.word = word
        result.en_translation = en_translation

        return result

    def propagate(
        self, word: str, en_translation: str, description: str
    ) -> WordbankWordDetails:
        """
        Generate complete word details using an LLM from minimal input.

        This function uses Marvin with Google Gemini to generate a complete WordbankWordDetails
        object from just a word, translation, and description. The LLM will:
        - Detect the language and set language_code
        - Expand the description if needed
        - Generate 2-3 example sentences using the word
        - Create an image description for flashcard memorization

        If the word already exists in the database with complete details (including image_description),
        it will reuse that data instead of calling the LLM.

        Args:
            word: The word in the target language
            en_translation: The English translation
            description: Context or description to narrow down the meaning

        Returns:
            Complete WordbankWordDetails object
        """
        result = self._generate_word_details(word, en_translation, description)
        self._generate_img(result)
        self.upsert(result)
        return result

    def _generate_img(self, details: WordbankWordDetails):
        """
        Generate flashcard image for the word details.

        Checks if the image already exists on disk before generating.
        If the image file exists, skips generation.

        Args:
            details: The word details to generate an image for
        """
        # Determine the file name
        file_name = details.en_translation.replace(" ", "_") + ".jpg"
        output_file = (
            Path(__file__).parent.parent.absolute()
            / "content"
            / "images"
            / "wordbank"
            / file_name
        )

        # Check if image already exists
        if details.image_file and output_file.exists():
            print(f"Image file already exists at {output_file} - skipping generation")
            return

        # Generate new image
        print(f"Generating new image for '{details.word}'")
        prompt = f"""
You are used to generate images for flash cards used to learn new words in foreign languages.
Use a simple, infographic visual style. Do not include any additional text, labels, unless 
explicitly requested in the image description.

Generate the following flashcard image:
{details.image_description}

"""
        result = self.imagen.models.generate_images(
            model="models/imagen-4.0-generate-001",
            prompt=prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1",
                image_size="1K",
            ),
        )

        if not result.generated_images:
            print("No images generated.")
            return

        if len(result.generated_images) != 1:
            print("Number of images generated does not match the requested number.")

        details.image_file = file_name
        for n, generated_image in enumerate(result.generated_images):
            generated_image.image.save(output_file)

    def _load(self) -> dict[tuple[str, str], WordbankWordDetails]:
        """Load all wordbank data from JSONL file into memory."""
        if self._cache is not None:
            return self._cache

        self._cache = {}

        if not self.data_path.exists():
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            return self._cache

        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    details = WordbankWordDetails(**data)
                    key = (details.word, details.en_translation)
                    self._cache[key] = details

        return self._cache

    def _save(self) -> None:
        """Save all wordbank data to JSONL file."""
        if self._cache is None:
            return

        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.data_path, "w", encoding="utf-8") as f:
            for details in self._cache.values():
                json.dump(asdict(details), f, ensure_ascii=False)
                f.write("\n")


def main():
    temp_wordbank = WordBank(data_path="./test_data.jsonl")
    temp_wordbank.propagate("猫", "cat", "The common household pet - a cat")

    for itm in temp_wordbank.get_all():
        print(itm)


if __name__ == "__main__":
    main()
