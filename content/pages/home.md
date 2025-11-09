Title: Home
Date: 2025-11-08 10:00
Modified: 2025-11-08 10:00
Status: published
Author: Ted
save_as: index.html

# Welcome to Ted's 日本語 Workbook

> **Look at the top of this page!** You'll see our custom `say_hi` filter in action, greeting the page author.

Welcome to my Japanese language learning journey!

## About This Site

This workbook is a collection of Japanese language learning materials, exercises, and notes. I'm documenting my progress as I study 日本語 (Nihongo - Japanese).

## Current Focus

I'm currently working on:

- **Hiragana** (ひらがな) - The basic Japanese phonetic writing system
- **Basic Vocabulary** - Common words and phrases for everyday conversation
- **Grammar Fundamentals** - Understanding Japanese sentence structure

## Recent Progress

### Hiragana Practice

I've been practicing writing and reading hiragana characters. Here are some basics:

- あ (a) - The first character
- い (i) - The second character
- う (u) - The third character
- え (e) - The fourth character
- お (o) - The fifth character

### First Words

Some simple words I've learned:

- こんにちは (Konnichiwa) - Hello
- ありがとう (Arigatou) - Thank you
- さようなら (Sayounara) - Goodbye

## Demo of Custom Filter

The greeting at the top of this page was generated using our custom `say_hi` Jinja filter!

In templates, you can use it like this:

```jinja2
{{ page.author | say_hi }}
```

Which produces the greeting you see in the colored box at the top: "Hello Ted"

The `say_hi` filter is a custom Jinja2 filter defined in the `plugins/say_hi/` directory. It takes any string and returns a friendly greeting.

## Next Steps

- Complete all hiragana characters
- Start learning katakana (カタカナ)
- Build a vocabulary list of 100 common words
- Practice basic sentence patterns

---

Thanks for visiting my Japanese learning workbook!
