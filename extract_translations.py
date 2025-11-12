#!/usr/bin/env python3
"""
Extract Japanese words and their English translations from ja-extract.jsonl.
Creates a simplified JSON file mapping words to lists of English definitions.
"""

import json
from pathlib import Path
from collections import defaultdict


def main():
    input_file = Path("data/ja-extract.jsonl")
    output_file = Path("data/ja-translations.json")

    # Dictionary to store word -> list of translations
    word_translations = defaultdict(set)

    print(f"Reading {input_file}...")
    line_count = 0
    ja_entries = 0
    entries_with_translations = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
            if line_count % 50000 == 0:
                print(f"  Processed {line_count:,} lines...")

            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                print(f"Warning: Failed to parse line {line_count}")
                continue

            # Only process Japanese entries
            if entry.get('lang_code') != 'ja':
                continue

            ja_entries += 1
            word = entry.get('word', '')

            if not word:
                continue

            # Look for English translations in the translations field
            translations = entry.get('translations', [])
            has_english = False

            for trans in translations:
                if trans.get('lang_code') == 'en':
                    english_word = trans.get('word', '').strip()
                    if english_word:
                        word_translations[word].add(english_word)
                        has_english = True

            if has_english:
                entries_with_translations += 1

    print(f"\nProcessing complete!")
    print(f"  Total lines: {line_count:,}")
    print(f"  Japanese entries: {ja_entries:,}")
    print(f"  Entries with English translations: {entries_with_translations:,}")
    print(f"  Unique Japanese words with translations: {len(word_translations):,}")

    # Convert sets to sorted lists for JSON serialization
    word_translations_dict = {
        word: sorted(list(translations))
        for word, translations in sorted(word_translations.items())
    }

    print(f"\nWriting to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(word_translations_dict, f, ensure_ascii=False, indent=2)

    print(f"Done! Created {output_file}")
    print(f"  Contains {len(word_translations_dict):,} Japanese words")

    # Show some examples
    print("\nExample entries:")
    for i, (word, translations) in enumerate(word_translations_dict.items()):
        if i >= 5:
            break
        print(f"  {word}: {translations}")


if __name__ == "__main__":
    main()
