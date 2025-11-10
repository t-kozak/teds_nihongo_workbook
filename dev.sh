#!/usr/bin/env zsh

set -e

case "$1" in
  serve)
    echo "Starting development server..."
    uv run pelican --autoreload --listen
    ;;
  build)
    echo "Building site..."
    uv run pelican content -o output -s pelicanconf.py
    ;;
  build-prod)
    echo "Building site for production..."
    uv run pelican content -o doc -s publishconf.py
    ;;
  clean)
    echo "Cleaning output..."
    uv run pelican --delete-output
    ;;
  *)
    echo "Usage: $0 {serve|build|build-prod|clean}"
    echo ""
    echo "  serve       Start development server with auto-reload"
    echo "  build       Build the static site (development)"
    echo "  build-prod  Build the static site (production)"
    echo "  clean       Clean the output directory"
    exit 1
    ;;
esac
