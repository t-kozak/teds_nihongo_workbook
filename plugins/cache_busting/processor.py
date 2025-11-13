"""
Cache Busting Processor

Handles the actual asset fingerprinting and HTML rewriting logic.
"""

import hashlib
import re
import shutil
from pathlib import Path
from typing import Dict, Set


class CacheBustingProcessor:
    """Processes static assets and HTML files for cache busting."""

    def __init__(self, output_path: str, siteurl: str, theme_static_dir: str):
        """
        Initialize the processor.

        Args:
            output_path: Path to Pelican's output directory
            siteurl: The SITEURL from Pelican settings
            theme_static_dir: The THEME_STATIC_DIR from Pelican settings
        """
        self.output_path = Path(output_path)
        self.siteurl = siteurl.rstrip('/')
        self.theme_static_dir = theme_static_dir
        # Maps original filename to hashed filename (relative paths from output root)
        self.asset_map: Dict[str, str] = {}
        # Extensions to process
        self.asset_extensions = {'.css', '.js'}

    def _calculate_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of file contents.

        Args:
            file_path: Path to the file

        Returns:
            First 8 characters of the MD5 hash
        """
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()[:8]

    def _get_hashed_filename(self, original_path: Path, content_hash: str) -> Path:
        """
        Generate a new filename with the content hash.

        Args:
            original_path: Original file path
            content_hash: Content hash to include

        Returns:
            New path with hash in filename (e.g., main.a3f5b2c.css)
        """
        stem = original_path.stem
        suffix = original_path.suffix
        new_name = f"{stem}.{content_hash}{suffix}"
        return original_path.parent / new_name

    def _find_assets(self) -> Set[Path]:
        """
        Find all CSS and JS files in the output directory.

        Returns:
            Set of paths to asset files
        """
        assets = set()
        for ext in self.asset_extensions:
            # Use rglob to find files recursively
            assets.update(self.output_path.rglob(f'*{ext}'))
        return assets

    def _create_hashed_assets(self):
        """
        Create hashed copies of all assets and build the mapping.
        """
        assets = self._find_assets()

        for asset_path in assets:
            # Calculate hash
            content_hash = self._calculate_hash(asset_path)

            # Generate new filename
            hashed_path = self._get_hashed_filename(asset_path, content_hash)

            # Copy to new filename
            shutil.copy2(asset_path, hashed_path)

            # Store mapping (use paths relative to output root)
            original_rel = asset_path.relative_to(self.output_path)
            hashed_rel = hashed_path.relative_to(self.output_path)

            # Convert to forward slashes for URLs
            original_url = str(original_rel).replace('\\', '/')
            hashed_url = str(hashed_rel).replace('\\', '/')

            self.asset_map[original_url] = hashed_url

            print(f"[Cache Busting] {original_url} -> {hashed_url}")

    def _update_html_files(self):
        """
        Update all HTML files to reference hashed assets.
        """
        html_files = list(self.output_path.rglob('*.html'))

        for html_path in html_files:
            # Read the HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Track if we made any changes
            modified = False

            # Replace references to assets
            for original_url, hashed_url in self.asset_map.items():
                # Pattern 1: Standard HTML attributes (href, src)
                # Match: href="...original_url" or src="...original_url"
                # Handle both with and without SITEURL prefix
                patterns = [
                    # With SITEURL prefix
                    (
                        rf'((?:href|src)=")({re.escape(self.siteurl)}/)?{re.escape(original_url)}(")',
                        rf'\1\2{hashed_url}\3'
                    ),
                ]

                # Also handle root-relative URLs (starting with /)
                if not self.siteurl:
                    patterns.append((
                        rf'((?:href|src)=")/{re.escape(original_url)}(")',
                        rf'\1/{hashed_url}\2'
                    ))

                for pattern, replacement in patterns:
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        modified = True
                        content = new_content

                # Pattern 2: ES module imports
                # Match: from '...original_url' or from "...original_url"
                # Also match: import('...original_url')
                import_patterns = [
                    (
                        rf"(from\s+['\"])({re.escape(self.siteurl)}/)?{re.escape(original_url)}(['\"])",
                        rf"\1\2{hashed_url}\3"
                    ),
                    (
                        rf"(import\s*\(['\"])({re.escape(self.siteurl)}/)?{re.escape(original_url)}(['\"])",
                        rf"\1\2{hashed_url}\3"
                    ),
                ]

                for pattern, replacement in import_patterns:
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        modified = True
                        content = new_content

            # Write back if modified
            if modified:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                rel_path = html_path.relative_to(self.output_path)
                print(f"[Cache Busting] Updated references in {rel_path}")

    def _update_js_files(self):
        """
        Update JavaScript files to reference hashed assets in import statements.
        """
        js_files = list(self.output_path.rglob('*.js'))

        for js_path in js_files:
            # Skip if this is one of the original (unhashed) files
            # We want to update the hashed versions
            rel_path = js_path.relative_to(self.output_path)
            rel_url = str(rel_path).replace('\\', '/')

            # Read the JS content
            with open(js_path, 'r', encoding='utf-8') as f:
                content = f.read()

            modified = False

            # Replace references to assets in import statements
            for original_url, hashed_url in self.asset_map.items():
                # Pattern: import ... from './module.js' or import('./module.js')
                # We need to handle relative imports carefully

                # Extract just the filename for relative imports
                original_filename = Path(original_url).name
                hashed_filename = Path(hashed_url).name

                # Pattern for relative imports
                patterns = [
                    # from './file.js' or from "../file.js"
                    (
                        rf"(from\s+['\"]\.+/.*?){re.escape(original_filename)}(['\"])",
                        rf"\1{hashed_filename}\2"
                    ),
                    # import('./file.js') or import("../file.js")
                    (
                        rf"(import\s*\(['\"]\.+/.*?){re.escape(original_filename)}(['\"])",
                        rf"\1{hashed_filename}\2"
                    ),
                ]

                for pattern, replacement in patterns:
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        modified = True
                        content = new_content

            # Write back if modified
            if modified:
                with open(js_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[Cache Busting] Updated imports in {rel_url}")

    def _update_css_files(self):
        """
        Update CSS files to reference hashed assets in @import and url() statements.
        """
        css_files = list(self.output_path.rglob('*.css'))

        for css_path in css_files:
            rel_path = css_path.relative_to(self.output_path)
            rel_url = str(rel_path).replace('\\', '/')

            # Read the CSS content
            with open(css_path, 'r', encoding='utf-8') as f:
                content = f.read()

            modified = False

            # Replace references to assets in @import and url() statements
            for original_url, hashed_url in self.asset_map.items():
                # Extract just the filename for relative imports
                original_filename = Path(original_url).name
                hashed_filename = Path(hashed_url).name

                # Pattern 1: @import url("file.css") or @import "file.css"
                patterns = [
                    # @import url("file.css")
                    (
                        rf'(@import\s+url\(["\']?)([^"\']*?){re.escape(original_filename)}(["\']?\))',
                        rf'\1\2{hashed_filename}\3'
                    ),
                    # @import "file.css"
                    (
                        rf'(@import\s+["\'])([^"\']*?){re.escape(original_filename)}(["\'])',
                        rf'\1\2{hashed_filename}\3'
                    ),
                    # url("file.css") or url('file.css') - for other references
                    (
                        rf'(url\(["\']?)([^"\']*?){re.escape(original_filename)}(["\']?\))',
                        rf'\1\2{hashed_filename}\3'
                    ),
                ]

                for pattern, replacement in patterns:
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        modified = True
                        content = new_content

            # Write back if modified
            if modified:
                with open(css_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[Cache Busting] Updated @import/url() in {rel_url}")

    def _remove_original_assets(self):
        """
        Remove the original unhashed asset files.
        """
        for original_url in self.asset_map.keys():
            original_path = self.output_path / original_url
            if original_path.exists():
                original_path.unlink()
                print(f"[Cache Busting] Removed original {original_url}")

    def process(self):
        """
        Main processing method. Orchestrates the entire cache busting process.
        """
        print("[Cache Busting] Starting asset fingerprinting...")

        # Step 1: Create hashed versions of all assets
        self._create_hashed_assets()

        if not self.asset_map:
            print("[Cache Busting] No assets found to fingerprint")
            return

        # Step 2: Update HTML files to reference hashed assets
        self._update_html_files()

        # Step 3: Update CSS files to reference hashed assets in @import/url()
        self._update_css_files()

        # Step 4: Update JS files to reference hashed assets in imports
        self._update_js_files()

        # Step 5: Remove original unhashed files
        self._remove_original_assets()

        print(f"[Cache Busting] Processed {len(self.asset_map)} assets")
