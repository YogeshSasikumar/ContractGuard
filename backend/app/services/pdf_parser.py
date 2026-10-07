"""
PDF Text Extraction Service using PyMuPDF (fitz)
Extracts text from uploaded PDF files with page-level tracking.
"""

import fitz  # PyMuPDF
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Extracts and cleans text from PDF documents."""

    def extract_text(self, pdf_path: str | Path) -> dict:
        """
        Extract text from a PDF file with page-level tracking.
        
        Returns:
            dict with keys:
                - full_text: str (entire document text)
                - pages: list[dict] (page number + text per page)
                - total_pages: int
                - metadata: dict (title, author, etc.)
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        pages = []
        full_text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            cleaned = self._clean_text(text)
            
            if cleaned.strip():
                pages.append({
                    "page_number": page_num + 1,
                    "text": cleaned,
                    "char_count": len(cleaned)
                })
                full_text_parts.append(cleaned)

        metadata = doc.metadata or {}
        doc.close()

        return {
            "full_text": "\n\n".join(full_text_parts),
            "pages": pages,
            "total_pages": len(pages),
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
            }
        }

    def _clean_text(self, text: str) -> str:
        """Clean extracted text: fix encoding issues, normalize whitespace."""
        if not text:
            return ""
        
        # Fix common PDF extraction artifacts
        text = text.replace("\x00", "")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # Fix hyphenated line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse excessive newlines
        text = re.sub(r"[ \t]{2,}", " ", text)  # Collapse excessive spaces
        text = re.sub(r"^\s+$", "", text, flags=re.MULTILINE)  # Remove blank lines with spaces
        
        return text.strip()


pdf_parser = PDFParser()
