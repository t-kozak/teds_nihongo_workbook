# Cache Busting Plugin

A Pelican plugin that adds content-based hash fingerprinting to static assets (CSS and JavaScript files) for effective browser cache invalidation.

## How It Works

The plugin automatically:

1. **Hashes assets** - Calculates MD5 hash of each CSS/JS file's contents
2. **Creates hashed copies** - Generates new files with hash in filename (e.g., `main.js` → `main.17c28f59.js`)
3. **Updates HTML references** - Rewrites all HTML `<link>` and `<script>` tags to use hashed filenames
4. **Updates CSS @import statements** - Rewrites `@import` and `url()` references in CSS files
5. **Updates ES module imports** - Rewrites JavaScript `import` statements to use hashed filenames
6. **Removes originals** - Deletes the unhashed files

## Features

- **Content-based hashing**: Uses MD5 hash (8 characters) of file contents
- **CSS @import support**: Updates `@import url()` and `@import "file"` statements in CSS files
- **ES6 module support**: Updates `import` statements in JavaScript files
- **Preserves directory structure**: Hashed files stay in same location as originals
- **Production-only**: Only runs when building with `publishconf.py`

## Usage

The plugin is already configured to run only for production builds. Simply use:

```bash
./dev.sh build-prod
```

For development builds (without cache busting):

```bash
./dev.sh build
```

## Example Output

### HTML - Before:
```html
<link rel="stylesheet" href="/theme/css/main.css" />
<script type="module" src="/theme/js/main.js"></script>
```

### HTML - After:
```html
<link rel="stylesheet" href="/theme/css/main.8dd0d5b5.css" />
<script type="module" src="/theme/js/main.17c28f59.js"></script>
```

### CSS @import - Before:
```css
@import url("reset.css");
@import url("fonts.css");
```

### CSS @import - After:
```css
@import url("reset.b50cc9c4.css");
@import url("fonts.e5ffbd53.css");
```

### JavaScript imports - Before:
```javascript
import { initFeature } from './modules/feature.js';
```

### JavaScript imports - After:
```javascript
import { initFeature } from './modules/feature.6fde0d30.js';
```

## Browser Caching

With this plugin, you can set aggressive cache headers on your web server:

```
Cache-Control: public, max-age=31536000, immutable
```

When you update your assets, the filename changes automatically, so browsers will fetch the new version.

## Configuration

The plugin is registered in [publishconf.py](../../publishconf.py):

```python
PLUGINS.append('cache_busting')
```

No additional configuration is needed.
