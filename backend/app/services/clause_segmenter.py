"""
Clause Segmentation Service
Splits contract text into individual clauses using rule-based + NLP heuristics.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClauseSegmenter:
    """Segments contract text into individual clauses for analysis."""

    # Patterns that indicate section/clause headings
    HEADING_PATTERNS = [
        # Numbered sections: "1.", "1.1", "1.1.1", "Section 1", "Article 1"
        re.compile(r"^(?:Section|Article|SECTION|ARTICLE)\s+\d+", re.MULTILINE),
        re.compile(r"^\d+\.\d*\s+[A-Z]", re.MULTILINE),
        # Uppercase headings: "INDEMNIFICATION", "LIMITATION OF LIABILITY"
        re.compile(r"^[A-Z][A-Z\s]{5,}$", re.MULTILINE),
        # Lettered subsections: "(a)", "(b)", "(i)", "(ii)"
        re.compile(r"^\s*\([a-z]\)\s+", re.MULTILINE),
        re.compile(r"^\s*\([ivx]+\)\s+", re.MULTILINE),
    ]

    # Minimum clause length (characters) to be considered valid
    MIN_CLAUSE_LENGTH = 50
    # Maximum clause length before splitting further
    MAX_CLAUSE_LENGTH = 2000

    def segment(self, text: str, pages: list[dict] | None = None) -> list[dict]:
        """
        Segment contract text into individual clauses.

        Args:
            text: Full contract text
            pages: Optional page-level text for page number tracking

        Returns:
            List of clause dicts with keys: text, section_heading, page_number
        """
        if not text or not text.strip():
            return []

        # Step 1: Split by major section headings
        sections = self._split_by_headings(text)

        # Step 2: Split long sections into paragraphs
        clauses = []
        for section in sections:
            if len(section["text"]) > self.MAX_CLAUSE_LENGTH:
                sub_clauses = self._split_by_paragraphs(section)
                clauses.extend(sub_clauses)
            elif len(section["text"]) >= self.MIN_CLAUSE_LENGTH:
                clauses.append(section)

        # Step 3: Assign page numbers if page data is available
        if pages:
            clauses = self._assign_page_numbers(clauses, pages)

        # Step 4: Assign IDs
        for idx, clause in enumerate(clauses):
            clause["id"] = idx + 1

        logger.info(f"Segmented document into {len(clauses)} clauses")
        return clauses

    def _split_by_headings(self, text: str) -> list[dict]:
        """Split text by detected section headings."""
        # Find all heading positions
        heading_positions = []
        for pattern in self.HEADING_PATTERNS:
            for match in pattern.finditer(text):
                heading_positions.append({
                    "start": match.start(),
                    "heading": match.group().strip()
                })

        # Sort by position and deduplicate nearby headings
        heading_positions.sort(key=lambda x: x["start"])
        heading_positions = self._deduplicate_positions(heading_positions)

        if not heading_positions:
            # No headings found — split by double newlines
            return self._split_by_paragraphs({"text": text, "section_heading": "General"})

        # Extract text between headings
        sections = []
        for i, heading in enumerate(heading_positions):
            start = heading["start"]
            end = heading_positions[i + 1]["start"] if i + 1 < len(heading_positions) else len(text)
            section_text = text[start:end].strip()

            if len(section_text) >= self.MIN_CLAUSE_LENGTH:
                sections.append({
                    "text": section_text,
                    "section_heading": self._clean_heading(heading["heading"]),
                    "page_number": None
                })

        # Handle text before first heading
        if heading_positions and heading_positions[0]["start"] > self.MIN_CLAUSE_LENGTH:
            preamble = text[:heading_positions[0]["start"]].strip()
            if len(preamble) >= self.MIN_CLAUSE_LENGTH:
                sections.insert(0, {
                    "text": preamble,
                    "section_heading": "Preamble",
                    "page_number": None
                })

        return sections

    def _split_by_paragraphs(self, section: dict) -> list[dict]:
        """Split a section into paragraph-level clauses."""
        text = section.get("text", "")
        heading = section.get("section_heading", "General")

        paragraphs = re.split(r"\n\s*\n", text)
        clauses = []

        for para in paragraphs:
            para = para.strip()
            if len(para) >= self.MIN_CLAUSE_LENGTH:
                clauses.append({
                    "text": para,
                    "section_heading": heading,
                    "page_number": section.get("page_number")
                })

        return clauses if clauses else [section]

    def _deduplicate_positions(self, positions: list[dict], min_gap: int = 20) -> list[dict]:
        """Remove heading positions that are too close together."""
        if not positions:
            return []
        
        deduped = [positions[0]]
        for pos in positions[1:]:
            if pos["start"] - deduped[-1]["start"] >= min_gap:
                deduped.append(pos)
        return deduped

    def _clean_heading(self, heading: str) -> str:
        """Clean and normalize a section heading."""
        heading = heading.strip()
        heading = re.sub(r"^(?:Section|Article|SECTION|ARTICLE)\s+\d+\.?\s*", "", heading)
        heading = re.sub(r"^\d+\.?\d*\.?\s*", "", heading)
        heading = heading.strip(". \t")
        return heading.title() if heading.isupper() else heading

    def _assign_page_numbers(self, clauses: list[dict], pages: list[dict]) -> list[dict]:
        """Assign page numbers to clauses by finding which page contains each clause's text."""
        for clause in clauses:
            clause_start = clause["text"][:80]  # Use first 80 chars for matching
            for page in pages:
                if clause_start in page["text"]:
                    clause["page_number"] = page["page_number"]
                    break
        return clauses


clause_segmenter = ClauseSegmenter()
