# Ted's Nihongo Workbook

A static website generator for Japanese language learning materials, built with Pelican and managed with uv.

## Commands

- `uv run pelican content` - Build the site
- `uv run pelican -r -l` - Start development server with auto-reload
- `uv run pelican content -s publishconf.py` - Build for production

## Structure

- `content/` - Source content files (Markdown)
- `output/` - Generated static site
- `plugins/` - Custom Pelican plugins
- `themes/` - Custom themes (optional)
