import json
import tempfile
from pathlib import Path

import pytest

from wordbank import WordBank, WordbankWordDetails


@pytest.fixture
def temp_wordbank():
    """Create a temporary WordBank instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir) / "test_wordbank.jsonl"
        yield WordBank(data_path=str(data_path), agent=None)


@pytest.fixture
def sample_word_details():
    """Create sample WordbankWordDetails for testing."""
    return WordbankWordDetails(
        word="猫",
        en_translation="cat",
        language_code="ja",
        examples=["猫が好きです。", "猫は可愛いです。"],
        description="A common domestic pet animal",
        image_description="A cute cat sitting on a windowsill",
        image_file="",
    )


@pytest.fixture
def another_word_details():
    """Create another sample WordbankWordDetails for testing."""
    return WordbankWordDetails(
        word="犬",
        en_translation="dog",
        language_code="ja",
        examples=["犬を飼っています。", "犬が走っています。"],
        description="A common domestic pet animal, loyal companion",
        image_description="A friendly dog playing in a park",
        image_file="",
    )


@pytest.mark.parametrize(
    "word,translation,expected",
    [
        ("猫", "cat", True),
        ("犬", "dog", False),
        ("猫", "kitten", False),
    ],
)
def test_contains(temp_wordbank, sample_word_details, word, translation, expected):
    """Test checking if a word-translation pair exists."""
    # Add a word to the wordbank
    temp_wordbank.upsert(sample_word_details)

    # Check if the word exists
    assert temp_wordbank.contains(word, translation) == expected


def test_contains_empty_wordbank(temp_wordbank):
    """Test contains on an empty wordbank."""
    assert temp_wordbank.contains("猫", "cat") is False


def test_get_existing_word(temp_wordbank, sample_word_details):
    """Test retrieving an existing word-translation pair."""
    temp_wordbank.upsert(sample_word_details)

    result = temp_wordbank.get("猫", "cat")

    assert result is not None
    assert result.word == "猫"
    assert result.en_translation == "cat"
    assert result.language_code == "ja"
    assert len(result.examples) == 2
    assert result.description == "A common domestic pet animal"


def test_get_nonexistent_word(temp_wordbank):
    """Test retrieving a non-existent word-translation pair."""
    result = temp_wordbank.get("猫", "cat")
    assert result is None


def test_get_wrong_translation(temp_wordbank, sample_word_details):
    """Test that getting a word with wrong translation returns None."""
    temp_wordbank.upsert(sample_word_details)

    # Same word, different translation
    result = temp_wordbank.get("猫", "kitten")
    assert result is None


def test_upsert_new_word(temp_wordbank, sample_word_details):
    """Test inserting a new word."""
    temp_wordbank.upsert(sample_word_details)

    result = temp_wordbank.get("猫", "cat")
    assert result is not None
    assert result.word == sample_word_details.word
    assert result.en_translation == sample_word_details.en_translation


def test_upsert_update_existing_word(temp_wordbank, sample_word_details):
    """Test updating an existing word-translation pair."""
    # Insert initial word
    temp_wordbank.upsert(sample_word_details)

    # Update with new details
    updated_details = WordbankWordDetails(
        word="猫",
        en_translation="cat",
        language_code="ja",
        examples=["新しい例文です。"],
        description="Updated description",
        image_description="Updated image description",
        image_file="new-uuid",
    )
    temp_wordbank.upsert(updated_details)

    result = temp_wordbank.get("猫", "cat")
    assert result is not None
    assert result.description == "Updated description"
    assert result.image_uuid == "new-uuid"
    assert len(result.examples) == 1


def test_upsert_multiple_words(
    temp_wordbank, sample_word_details, another_word_details
):
    """Test inserting multiple words."""
    temp_wordbank.upsert(sample_word_details)
    temp_wordbank.upsert(another_word_details)

    assert temp_wordbank.contains("猫", "cat")
    assert temp_wordbank.contains("犬", "dog")

    cat = temp_wordbank.get("猫", "cat")
    dog = temp_wordbank.get("犬", "dog")

    assert cat is not None
    assert dog is not None
    assert cat.word != dog.word


def test_persistence(sample_word_details):
    """Test that data persists across WordBank instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = Path(tmpdir) / "test_wordbank.jsonl"

        # Create first instance and add data
        wb1 = WordBank(data_path=str(data_path), agent=None)
        wb1.upsert(sample_word_details)

        # Create second instance with same path
        wb2 = WordBank(data_path=str(data_path), agent=None)

        # Verify data is accessible from second instance
        result = wb2.get("猫", "cat")
        assert result is not None
        assert result.word == "猫"
        assert result.en_translation == "cat"


def test_jsonl_format(temp_wordbank, sample_word_details):
    """Test that the JSONL file is correctly formatted."""
    temp_wordbank.upsert(sample_word_details)

    # Read the file directly
    with open(temp_wordbank.data_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 1

    # Parse the JSON line
    data = json.loads(lines[0])
    assert data["word"] == "猫"
    assert data["en_translation"] == "cat"
    assert data["language_code"] == "ja"


def test_multiple_words_jsonl_format(
    temp_wordbank, sample_word_details, another_word_details
):
    """Test JSONL format with multiple words."""
    temp_wordbank.upsert(sample_word_details)
    temp_wordbank.upsert(another_word_details)

    # Read the file directly
    with open(temp_wordbank.data_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 2

    # Each line should be valid JSON
    for line in lines:
        data = json.loads(line)
        assert "word" in data
        assert "en_translation" in data
        assert "language_code" in data


def test_multiple_meanings_same_word(temp_wordbank):
    """Test that the same word can have different meanings with different translations."""
    # Add "run" as a verb
    run_verb = WordbankWordDetails(
        word="run",
        en_translation="move quickly on foot",
        language_code="en",
        examples=["I run every morning."],
        description="To move swiftly on foot",
        image_description="A person running",
        image_file="",
    )

    # Add "run" as a noun
    run_noun = WordbankWordDetails(
        word="run",
        en_translation="a point scored in cricket",
        language_code="en",
        examples=["He scored a run."],
        description="A point in cricket",
        image_description="A cricket player scoring",
        image_file="",
    )

    temp_wordbank.upsert(run_verb)
    temp_wordbank.upsert(run_noun)

    # Both meanings should be stored separately
    assert temp_wordbank.contains("run", "move quickly on foot")
    assert temp_wordbank.contains("run", "a point scored in cricket")

    verb_result = temp_wordbank.get("run", "move quickly on foot")
    noun_result = temp_wordbank.get("run", "a point scored in cricket")

    assert verb_result is not None
    assert noun_result is not None
    assert verb_result.description != noun_result.description


def test_empty_wordbank_operations(temp_wordbank):
    """Test operations on an empty wordbank."""
    # contains should return False
    assert temp_wordbank.contains("any", "word") is False

    # get should return None
    assert temp_wordbank.get("any", "word") is None


def test_special_characters_in_words(temp_wordbank):
    """Test handling of special characters in words."""
    special_word = WordbankWordDetails(
        word="être",
        en_translation="to be",
        language_code="fr",
        examples=["Je suis content d'être ici."],
        description="French verb meaning to be",
        image_description="A person existing",
        image_file="",
    )

    temp_wordbank.upsert(special_word)

    assert temp_wordbank.contains("être", "to be")
    result = temp_wordbank.get("être", "to be")
    assert result is not None
    assert result.word == "être"


def test_cache_consistency(temp_wordbank, sample_word_details):
    """Test that the cache remains consistent with file operations."""
    # Add a word
    temp_wordbank.upsert(sample_word_details)

    # Verify it's in cache
    assert temp_wordbank.contains("猫", "cat")

    # Update the word
    updated = WordbankWordDetails(
        word="猫",
        en_translation="cat",
        language_code="ja",
        examples=["新しい例文。"],
        description="Updated",
        image_description="Updated",
        image_file="uuid",
    )
    temp_wordbank.upsert(updated)

    # Verify cache has updated version
    result = temp_wordbank.get("猫", "cat")
    assert result.description == "Updated"
    assert result.image_uuid == "uuid"
