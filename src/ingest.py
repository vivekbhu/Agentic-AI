"""Document ingestion utilities.

This module contains helpers that convert source files into plain text for
downstream extraction and triage.
"""

from pypdf import PdfReader


def pdf_to_text(path: str) -> str:
    """Extract text from every page of a PDF.

    Args:
        path: Path to the input PDF.

    Returns:
        A single string containing text from all pages with page separators.
    """
    reader = PdfReader(path)
    parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        parts.append(f"\n--- Page {i + 1} ---\n{text}")
    return "\n".join(parts)
