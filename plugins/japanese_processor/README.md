# Japanese Text Processor Plugin

A unified Pelican plugin that combines word segmentation, English translation, and furigana annotation for Japanese text using LLM-based processing.

## Overview

This plugin **replaces and combines** the functionality of:
- **wordspan**: Wraps Japanese words in span elements with word boundaries
- **furigana**: Adds furigana (hiragana readings) above kanji

It provides superior functionality through:
- **Accurate word boundary detection** using LLM understanding of Japanese grammar
- **Contextual English translations** for each word based on sentence context
- **Intelligent furigana** only for kanji words (not pure hiragana/katakana)
- **High performance** through async batch processing with configurable batch size

## Features

### Word Segmentation
Uses Marvin Agent with LLM to accurately identify Japanese word boundaries, handling complex cases like:
- Verb conjugations (食べます, 行きました)
- Compound words (勉強します)
- Particles and grammatical elements (を, は, が)

### Contextual Translations
Provides English meanings that consider:
- Sentence context (not just dictionary definitions)
- Word function in the sentence
- Appropriate translations for particles and grammar

### Smart Furigana
Adds hiragana readings only when needed:
- ✅ Kanji words get furigana: `日本語` → `にほんご`
- ❌ Pure hiragana words don't: `です` (no furigana attribute)
- ❌ Pure katakana words don't: `コーヒー` (no furigana attribute)

## Output Format

Each Japanese word is wrapped in a span with data attributes:

```html
<span class="jp-word"
      data-en-translation="Japanese language"
      data-furigana="にほんご">日本語</span>
<span class="jp-word"
      data-en-translation="(object marker)">を</span>
<span class="jp-word"
      data-en-translation="study"
      data-furigana="べんきょう">勉強</span>
<span class="jp-word"
      data-en-translation="do (polite)">します</span>。
```

### Data Attributes

- **`data-en-translation`**: English meaning of the word (always present)
- **`data-furigana`**: Hiragana reading (only present if word contains kanji)

## Installation

1. **Add to your Pelican configuration** (`pelicanconf.py`):

```python
PLUGINS = [
    # ... other plugins ...
    "japanese_processor",  # Add this line
    # Remove "wordspan" and "furigana" if you had them
]
```

2. **Dependencies** (already in `pyproject.toml`):
   - `marvin` - LLM agent framework
   - `markupsafe` - Safe HTML handling
   - `redis` - Cache backend (optional, falls back gracefully if unavailable)

3. **Install Redis** (optional but highly recommended for cost savings):

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

4. **Environment Variables**: Configure your LLM API key:
```bash
export GOOGLE_AI_STUDIO_KEY="your-api-key-here"
```

## Configuration

### Redis Caching (Recommended!)

**The plugin includes built-in Redis caching to dramatically reduce LLM API costs.**

Caching is enabled by default and stores LLM responses for 30 days. Since the same Japanese phrases appear frequently across your content, this can reduce costs by **80-95%** on rebuilds.

#### Cache Configuration via Environment Variables

```bash
# Disable caching (not recommended)
export JAPANESE_PROCESSOR_CACHE_ENABLED="false"

# Change cache TTL (in seconds)
export JAPANESE_PROCESSOR_CACHE_TTL="604800"  # 7 days

# Configure Redis connection (if not using localhost)
export JAPANESE_PROCESSOR_REDIS_HOST="your-redis-host"
export JAPANESE_PROCESSOR_REDIS_PORT="6379"
```

#### How Caching Works

1. Each Japanese text segment's prompt is hashed (SHA256)
2. Before making an LLM API call, the cache is checked
3. **Cache HIT** → Return cached response (free, instant)
4. **Cache MISS** → Call LLM API and store response in cache
5. Cached entries automatically expire after TTL

#### Cache Statistics

The plugin logs cache performance:
```
[japanese_processor:cache] Connected to Redis at localhost:6379
[japanese_processor:cache] Cache HIT for prompt (length: 42)
[japanese_processor:cache] Cached response for prompt (length: 42)
```

#### Graceful Fallback

If Redis is unavailable, the plugin automatically disables caching and continues working:
```
[japanese_processor:cache] Redis connection failed: Connection refused
[japanese_processor:cache] Running without cache
```

### Batch Size

Adjust concurrent processing in `processor.py`:

```python
BATCH_SIZE = 10  # Number of text chunks to process concurrently
```

- **Higher values** = Faster processing, higher API costs
- **Lower values** = Slower processing, lower API costs

### Retry Attempts

Configure retry logic in `processor.py`:

```python
MAX_RETRIES = 3  # Number of retry attempts for failed LLM calls
```

### Model Selection

The plugin uses Google Gemini Flash Lite by default (configured in `processor.py`):

```python
model=GoogleModel(
    model_name="models/gemini-flash-lite-latest",
    provider=GoogleProvider(api_key=google_api_key),
)
```

This provides excellent quality at very low cost, especially when combined with caching.

## Performance

### Async Batch Processing

The plugin processes Japanese text segments in **async batches** for optimal performance:

1. Identifies all Japanese text chunks in the document
2. Groups them into batches (default: 10 chunks per batch)
3. Processes each batch concurrently using `asyncio.gather()`
4. Handles errors gracefully with retry logic

### Processing Flow

```
HTML Content
    ↓
Parse HTML (preserve tags)
    ↓
Identify Japanese text segments
    ↓
Group into batches of BATCH_SIZE
    ↓
Process batches concurrently
    ↓
Replace with annotated HTML
    ↓
Return complete HTML
```

## Error Handling

The plugin is designed to be **fault-tolerant**:

- **LLM failures**: Retries up to MAX_RETRIES times with exponential backoff
- **Invalid responses**: Falls back to original text if HTML extraction fails
- **Processing errors**: Logs errors and preserves original content
- **Script tags**: Skips JavaScript content automatically

## Usage in Templates

### CSS Styling

Style the word spans:

```css
.jp-word {
    cursor: pointer;
    border-bottom: 1px dotted #ccc;
    transition: background-color 0.2s;
}

.jp-word:hover {
    background-color: #ffffcc;
}
```

### JavaScript Interactivity

Access translations and furigana:

```javascript
document.querySelectorAll('.jp-word').forEach(word => {
    word.addEventListener('click', function() {
        const translation = this.dataset.enTranslation;
        const furigana = this.dataset.furigana;

        console.log(`Word: ${this.textContent}`);
        console.log(`Translation: ${translation}`);
        if (furigana) {
            console.log(`Reading: ${furigana}`);
        }
    });
});
```

### Display Furigana

Show furigana above words:

```javascript
document.querySelectorAll('.jp-word[data-furigana]').forEach(word => {
    const furigana = word.dataset.furigana;
    word.innerHTML = `<ruby>${word.textContent}<rt>${furigana}</rt></ruby>`;
});
```

## Migration from Old Plugins

If you were using `wordspan` and `furigana`:

1. **Remove old plugins** from `pelicanconf.py`:
```python
PLUGINS = [
    # Remove these lines:
    # "wordspan",
    # "furigana",

    # Add this instead:
    "japanese_processor",
]
```

2. **Update CSS** if needed:
   - Old: Separate handling for `.jp-word` and `<ruby>` tags
   - New: Use `.jp-word` with `data-*` attributes

3. **Update JavaScript** to use new data attributes:
   - Old: May have used different attribute names
   - New: `data-en-translation` and `data-furigana`

## Development

### Running Tests

```bash
uv run python -c "exec(open('plugins/japanese_processor/test_processor.py').read())"
```

### Adding New Features

The processor is modular:
- `processor.py`: Core processing logic
- `__init__.py`: Pelican integration
- Modify `_build_llm_prompt()` to adjust LLM behavior

### Debugging

Enable verbose logging:
```python
# In processor.py
print(f"[japanese_processor] Debug: {message}")
```

## Troubleshooting

### No output/processing not working

Check that:
1. Plugin is registered in `PLUGINS` list
2. OpenAI API key is set in environment
3. Marvin is properly installed: `uv pip list | grep marvin`

### LLM calls failing

Check:
1. API key is valid
2. Rate limits not exceeded
3. Model name is correct
4. Network connectivity

### Performance issues

Adjust:
1. Reduce `BATCH_SIZE` for lower concurrency
2. Ensure Redis is running for caching
3. Check cache statistics to verify caching is working

### Cache Management

```python
# Clear all cached entries
from plugins.japanese_processor.cache import get_cache

cache = get_cache()
cache.clear_all()

# Get cache statistics
stats = cache.get_stats()
print(stats)  # {'enabled': True, 'connected': True, 'entries': 1234}
```

### High API costs

If you're experiencing high costs:
1. **Verify caching is enabled**: Check for cache HIT messages in logs
2. **Ensure Redis is running**: `redis-cli ping` should return `PONG`
3. **Check cache TTL**: Longer TTL = more cache hits = lower costs
4. **Monitor cache size**: `redis-cli DBSIZE` shows total keys

## License

Same as parent project.

## Credits

- Built with [Marvin](https://www.askmarvin.ai/) for LLM agent functionality
- Uses OpenAI models for Japanese language understanding
- Inspired by original `wordspan` and `furigana` plugins
