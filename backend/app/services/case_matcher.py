"""
Case Matcher Service
Matches analyzed clauses to real-world legal cases from the knowledge base.
Uses sentence-transformer embeddings for semantic similarity.
Falls back to keyword matching if model unavailable.
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level state
_embedding_model = None
_case_embeddings = None
_is_embedding_loaded = False


def load_embedding_model() -> bool:
    """Load sentence-transformers model for semantic case matching."""
    global _embedding_model, _is_embedding_loaded

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading sentence-transformer (all-MiniLM-L6-v2) for case matching...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        _is_embedding_loaded = True
        logger.info("Sentence-transformer loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to load sentence-transformer: {e}")
        _is_embedding_loaded = False
        return False


class CaseMatcher:
    """Matches clause types to relevant real-world legal cases."""

    def __init__(self):
        self.cases: list[dict] = []
        self._case_texts: list[str] = []
        self._load_cases()

    def _load_cases(self):
        """Load case knowledge base from JSON."""
        cases_path = settings.data_dir / "case_knowledge_base.json"
        try:
            with open(cases_path, "r", encoding="utf-8") as f:
                self.cases = json.load(f)

            # Pre-build text for each case (for embedding)
            self._case_texts = [
                f"{c.get('case_name', '')} {c.get('clause_type', '')} {c.get('summary', '')} {c.get('lesson', '')}"
                for c in self.cases
            ]

            logger.info(f"Loaded {len(self.cases)} cases from knowledge base")
        except Exception as e:
            logger.error(f"Failed to load case knowledge base: {e}")
            self.cases = []
            self._case_texts = []

    def precompute_embeddings(self):
        """Pre-compute embeddings for all case summaries at startup."""
        global _case_embeddings

        if not _is_embedding_loaded or not self._case_texts:
            return

        try:
            _case_embeddings = _embedding_model.encode(
                self._case_texts, normalize_embeddings=True, show_progress_bar=False
            )
            logger.info(f"Pre-computed embeddings for {len(self._case_texts)} cases")
        except Exception as e:
            logger.error(f"Failed to pre-compute case embeddings: {e}")

    def find_matching_cases(
        self, clause_text: str = "", clause_type: str = "", risk_level: str = None, limit: int = 3
    ) -> list[dict]:
        """
        Find cases matching a clause using semantic similarity.
        Falls back to keyword matching if embeddings unavailable.

        Args:
            clause_text: The actual clause text (for embedding similarity)
            clause_type: The classified clause type
            risk_level: Optional risk level filter
            limit: Maximum number of cases to return

        Returns:
            List of matching case dicts with similarity scores
        """
        # Try embedding-based matching first
        if _is_embedding_loaded and _case_embeddings is not None and clause_text:
            return self._match_by_embedding(clause_text, clause_type, risk_level, limit)

        # Fall back to keyword matching
        return self._match_by_keywords(clause_type, risk_level, limit)

    def _match_by_embedding(
        self, clause_text: str, clause_type: str, risk_level: str = None, limit: int = 3
    ) -> list[dict]:
        """Match using cosine similarity of embeddings."""
        try:
            # Combine clause text with type for richer embedding
            query = f"{clause_type} {clause_text[:300]}"
            query_embedding = _embedding_model.encode(
                [query], normalize_embeddings=True, show_progress_bar=False
            )

            # Cosine similarity (already normalized, so dot product = cosine sim)
            similarities = np.dot(_case_embeddings, query_embedding.T).squeeze()

            # Get top matches
            top_indices = np.argsort(similarities)[::-1][:limit]

            matches = []
            for idx in top_indices:
                if similarities[idx] > 0.15:  # Minimum similarity threshold
                    case = self.cases[idx].copy()
                    case["similarity_score"] = round(float(similarities[idx]), 3)
                    matches.append(case)

            return matches

        except Exception as e:
            logger.error(f"Embedding matching failed: {e}")
            return self._match_by_keywords(clause_type, risk_level, limit)

    def _match_by_keywords(
        self, clause_type: str, risk_level: str = None, limit: int = 3
    ) -> list[dict]:
        """Fallback: match using keyword/string matching."""
        clause_type_lower = clause_type.lower().strip()

        matches = []
        for case in self.cases:
            case_type_lower = case["clause_type"].lower().strip()

            if case_type_lower == clause_type_lower:
                matches.append({"case": case, "relevance": 1.0})
                continue

            if clause_type_lower in case_type_lower or case_type_lower in clause_type_lower:
                matches.append({"case": case, "relevance": 0.8})
                continue

            if risk_level and case.get("risk_level") == risk_level:
                matches.append({"case": case, "relevance": 0.3})

        matches.sort(key=lambda x: x["relevance"], reverse=True)
        return [m["case"] for m in matches[:limit]]

    def get_all_cases(self) -> list[dict]:
        """Return all cases in the knowledge base."""
        return self.cases

    def get_cases_by_risk_level(self, risk_level: str) -> list[dict]:
        """Filter cases by risk level."""
        return [c for c in self.cases if c.get("risk_level", "").upper() == risk_level.upper()]

    def get_case_by_id(self, case_id: int) -> dict | None:
        """Get a specific case by its ID."""
        for case in self.cases:
            if case["id"] == case_id:
                return case
        return None


case_matcher = CaseMatcher()
