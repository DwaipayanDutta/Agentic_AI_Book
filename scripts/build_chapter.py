#!/usr/bin/env python3
"""
Build script for converting markdown chapters to PDF.
Requires: pandoc, wkhtmltopdf (or prince, weasyprint as alternatives)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple


class ChapterBuilder:
    """Build individual chapters from markdown to PDF."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.chapters_dir = self.repo_root / "chapters"
        self.appendices_dir = self.repo_root / "appendices"
        self.output_dir = self.repo_root / "pdfs"

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_chapter(self, chapter_spec: str) -> Optional[Path]:
        """
        Find a chapter file by number or path.

        Args:
            chapter_spec: Either chapter number (e.g., "01", "1") or partial path

        Returns:
            Path to the chapter file, or None if not found
        """
        # Try as chapter number first
        if chapter_spec.isdigit():
            chapter_num = int(chapter_spec)
            filename = f"chapter-{chapter_num:02d}-*.md"
        else:
            filename = chapter_spec

        # Search in chapters directory
        matching_files = list(self.chapters_dir.glob(f"**/{filename}"))
        if matching_files:
            return matching_files[0]

        # Search in appendices directory
        matching_files = list(self.appendices_dir.glob(f"**/{filename}"))
        if matching_files:
            return matching_files[0]

        return None

    def build_chapter_pandoc(self, markdown_path: Path) -> Tuple[bool, str]:
        """
        Build chapter using pandoc.

        Args:
            markdown_path: Path to markdown file

        Returns:
            Tuple of (success: bool, message: str)
        """
        output_path = self.output_dir / markdown_path.stem.replace("chapter-", "ch-") / ".pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pandoc command with common options
        cmd = [
            "pandoc",
            str(markdown_path),
            "-f", "markdown",
            "-t", "pdf",
            "-o", str(output_path),
            "--table-of-contents",
            "--number-sections",
            "--highlight-style", "espresso",
            "--pdf-engine=wkhtmltopdf",
            "--template", str(self.repo_root / "templates" / "default.latex"),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, f"Built: {output_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Build failed: {e.stderr}"
        except FileNotFoundError:
            return False, "Error: pandoc not found. Install with: pip install pandoc"

    def build_chapter_wkhtmltopdf(self, markdown_path: Path) -> Tuple[bool, str]:
        """
        Build chapter using pandoc + wkhtmltopdf.

        Args:
            markdown_path: Path to markdown file

        Returns:
            Tuple of (success: bool, message: str)
        """
        # First convert markdown to HTML with pandoc
        html_temp = self.output_dir / f"{markdown_path.stem}.html"

        cmd_pandoc = [
            "pandoc",
            str(markdown_path),
            "-f", "markdown",
            "-t", "html5",
            "-o", str(html_temp),
            "--standalone",
            "--css", str(self.repo_root / "styles" / "default.css"),
        ]

        try:
            subprocess.run(cmd_pandoc, capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return False, f"Pandoc conversion failed: {e}"

        # Then convert HTML to PDF with wkhtmltopdf
        output_path = self.output_dir / markdown_path.stem.replace("chapter-", "ch-") / ".pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd_wkhtmltopdf = [
            "wkhtmltopdf",
            "--page-size", "A4",
            "--margin-top", "0.75in",
            "--margin-right", "0.75in",
            "--margin-bottom", "0.75in",
            "--margin-left", "0.75in",
            "--header-line",
            "--footer-line",
            "--footer-center", "[page]",
            str(html_temp),
            str(output_path),
        ]

        try:
            subprocess.run(cmd_wkhtmltopdf, capture_output=True, check=True)
            html_temp.unlink()  # Clean up temp HTML
            return True, f"Built: {output_path}"
        except subprocess.CalledProcessError as e:
            return False, f"wkhtmltopdf conversion failed: {e}"
        except FileNotFoundError:
            return False, "Error: wkhtmltopdf not found. Install with: apt-get install wkhtmltopdf"

    def build(self, chapter_spec: str, engine: str = "pandoc") -> Tuple[bool, str]:
        """
        Build a chapter to PDF.

        Args:
            chapter_spec: Chapter number or path
            engine: Conversion engine (pandoc, wkhtmltopdf)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Find the chapter
        chapter_path = self.find_chapter(chapter_spec)
        if not chapter_path:
            return False, f"Chapter not found: {chapter_spec}"

        # Build using specified engine
        if engine == "pandoc":
            return self.build_chapter_pandoc(chapter_path)
        elif engine == "wkhtmltopdf":
            return self.build_chapter_wkhtmltopdf(chapter_path)
        else:
            return False, f"Unknown engine: {engine}"


def main():
    parser = argparse.ArgumentParser(
        description="Build chapters from markdown to PDF"
    )
    parser.add_argument(
        "chapter",
        help="Chapter number (e.g., 01, 1) or file path",
    )
    parser.add_argument(
        "--engine",
        choices=["pandoc", "wkhtmltopdf"],
        default="pandoc",
        help="PDF conversion engine to use",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory",
    )

    args = parser.parse_args()

    builder = ChapterBuilder(args.root)
    success, message = builder.build(args.chapter, args.engine)

    print(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
