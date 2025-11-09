# Ted's Nihongo Workbook

A static website generator for Japanese language learning materials, built with Pelican and managed with uv.

## Commands

Use the [dev.sh](dev.sh) script to manage the site:

- `./dev.sh serve` - Start development server with auto-reload
- `./dev.sh build` - Build the site (development)
- `./dev.sh build-prod` - Build the site (production)
- `./dev.sh clean` - Clean the output directory

## Structure

- `content/` - Source content files (Markdown)
- `output/` - Generated static site
- `plugins/` - Custom Pelican plugins
- `themes/` - Custom themes (optional)
