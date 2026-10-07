"""
Risk Scoring Engine
Maps clause types to risk levels and computes overall risk scores.
Uses probability × centrality formula when ML classifier is active.
Falls back to keyword-based classification when ML models are unavailable.
"""

import json
import re
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

# Centrality weight factor: centrality can boost risk by up to this fraction
CENTRALITY_WEIGHT = 0.5


class RiskScorer:
    """Classifies clauses and assigns risk levels."""

    def __init__(self):
        self.risk_mapping = {}
        self.clause_descriptions = {}
        self.clause_keywords = self._build_keyword_map()
        self._load_risk_mapping()

    def _load_risk_mapping(self):
        """Load the risk level mapping from JSON."""
        mapping_path = settings.data_dir / "risk_mapping.json"
        try:
            with open(mapping_path, "r") as f:
                data = json.load(f)

            # Build reverse mapping: clause_type -> risk_level
            for level in ["HIGH", "MEDIUM", "LOW"]:
                for clause_type in data.get(level, []):
                    self.risk_mapping[clause_type.lower()] = level

            self.clause_descriptions = data.get("clause_descriptions", {})
            logger.info(f"Loaded risk mapping with {len(self.risk_mapping)} clause types")
        except Exception as e:
            logger.error(f"Failed to load risk mapping: {e}")

    def get_risk_level(self, clause_type: str) -> str:
        """Look up risk level for a given clause type."""
        return self.risk_mapping.get(clause_type.lower(), "LOW")

    def get_description(self, clause_type: str) -> str:
        """Get the description for a clause type."""
        return self.clause_descriptions.get(
            clause_type, f"A {clause_type} clause detected in the contract."
        )

    def classify_clause_keyword(self, text: str) -> dict:
        """
        FALLBACK: Classify a clause using keyword matching.
        Used when ML models are unavailable.
        """
        text_lower = text.lower()
        scores = {}

        for clause_type, keywords in self.clause_keywords.items():
            score = 0
            for keyword in keywords:
                if re.search(keyword, text_lower):
                    score += 1
            if score > 0:
                scores[clause_type] = score / len(keywords)

        if not scores:
            return {
                "clause_type": "Uncategorized",
                "risk_level": "LOW",
                "confidence": 0.3,
                "description": "This clause does not match any known risk pattern.",
                "model": "keyword",
            }

        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] * 2.5, 0.95)
        risk_level = self.risk_mapping.get(best_type, "LOW")
        display_name = best_type.replace("/", "/").title()
        description = self.clause_descriptions.get(
            display_name, f"A {display_name} clause detected in the contract."
        )

        return {
            "clause_type": display_name,
            "risk_level": risk_level,
            "confidence": round(confidence, 3),
            "description": description,
            "model": "keyword",
        }

    def compute_clause_risk_score(
        self, confidence: float, centrality: float = 0.0
    ) -> float:
        """
        Compute per-clause risk score using probability × centrality.

        Formula: risk_score = confidence × (1 + centrality × CENTRALITY_WEIGHT)

        Args:
            confidence: Model probability (0-1)
            centrality: Graph degree centrality (0-1)

        Returns:
            Weighted risk score (0-1.5 range, capped at 1.0 for display)
        """
        score = confidence * (1.0 + centrality * CENTRALITY_WEIGHT)
        return min(round(score, 4), 1.0)

    def get_top_risky_clauses(self, clause_results: list[dict], n: int = 5) -> list[dict]:
        """
        Extract the top N riskiest clauses sorted by risk_score.
        
        Returns:
            List of compact clause dicts with id, clause_type, risk_level, risk_score, confidence.
        """
        scored = [c for c in clause_results if c.get("risk_score") is not None]
        scored.sort(key=lambda c: c.get("risk_score", 0), reverse=True)
        
        return [
            {
                "id": c.get("id", 0),
                "clause_type": c.get("clause_type", "Unknown"),
                "risk_level": c.get("risk_level", "LOW"),
                "risk_score": round(c.get("risk_score", 0), 4),
                "confidence": round(c.get("confidence", 0), 4),
            }
            for c in scored[:n]
        ]

    def compute_overall_risk(self, clause_results: list[dict]) -> dict:
        """
        Compute overall risk summary from classified clauses.
        Uses per-clause risk scores when available.
        Includes top risky clauses.
        """
        total = len(clause_results)
        if total == 0:
            return {
                "total_clauses": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "overall_risk_score": 0.0,
                "risk_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "top_risky_clauses": [],
            }

        high = sum(1 for c in clause_results if c.get("risk_level") == "HIGH")
        medium = sum(1 for c in clause_results if c.get("risk_level") == "MEDIUM")
        low = sum(1 for c in clause_results if c.get("risk_level") == "LOW")

        # Use per-clause risk scores if available, otherwise weight by level
        risk_weights = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.1}
        total_score = 0.0

        for c in clause_results:
            clause_score = c.get("risk_score")
            if clause_score is not None:
                # Use the centrality-weighted score, scaled by risk level
                level_weight = risk_weights.get(c.get("risk_level", "LOW"), 0.1)
                total_score += clause_score * level_weight
            else:
                # Fallback: use level weights only
                total_score += risk_weights.get(c.get("risk_level", "LOW"), 0.1)

        overall = (total_score / total) * 100
        overall = min(round(overall, 1), 100.0)

        return {
            "total_clauses": total,
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "overall_risk_score": overall,
            "risk_distribution": {
                "HIGH": round(high / total * 100, 1) if total > 0 else 0,
                "MEDIUM": round(medium / total * 100, 1) if total > 0 else 0,
                "LOW": round(low / total * 100, 1) if total > 0 else 0,
            },
            "top_risky_clauses": self.get_top_risky_clauses(clause_results),
        }

    def _build_keyword_map(self) -> dict[str, list[str]]:
        """Build keyword patterns for each clause type (fallback classifier)."""
        return {
            "indemnification": [
                "indemnif", "hold harmless", "defend and indemnify",
                "indemnity", "save harmless"
            ],
            "limitation of liability": [
                "limitation of liability", "limit of liability",
                "limited liability", "in no event shall.*liable",
                "aggregate liability", "shall not exceed"
            ],
            "uncapped liability": [
                "unlimited liability", "uncapped", "no limit.*liability",
                "without limitation.*damages"
            ],
            "ip ownership assignment": [
                "intellectual property.*assign", "ip.*assign",
                "work.*for.*hire", "all rights.*title.*interest",
                "assign.*patent", "assign.*copyright",
                "ownership of.*invention"
            ],
            "non-compete": [
                "non-compete", "noncompete", "not.*compete",
                "covenant not to compete", "competitive activity",
                "refrain from.*competing"
            ],
            "exclusivity": [
                "exclusive", "exclusivity", "sole.*right",
                "sole.*provider", "exclusive.*license",
                "exclusive.*agreement"
            ],
            "most favored nation": [
                "most favored", "most-favored", "mfn",
                "no less favorable", "most favoured"
            ],
            "anti-assignment": [
                "anti-assignment", "not.*assign", "shall not assign",
                "assignment.*prohibited", "without.*consent.*assign",
                "may not.*transfer"
            ],
            "change of control": [
                "change of control", "change in control",
                "merger.*acquisition", "controlling interest",
                "ownership change", "transfer of control"
            ],
            "liquidated damages": [
                "liquidated damages", "liquidated.*damage",
                "predetermined.*damage", "stipulated.*damage",
                "agreed.*damage.*amount"
            ],
            "termination for convenience": [
                "terminat.*convenience", "terminat.*without cause",
                "terminat.*any reason", "terminat.*no reason",
                "right to terminat.*at any time"
            ],
            "non-solicitation": [
                "non-solicitation", "nonsolicitation", "not.*solicit",
                "refrain.*soliciting", "shall not.*recruit"
            ],
            "rofr/rofo/rofn": [
                "right of first refusal", "rofr", "rofo", "rofn",
                "right of first offer", "right of first negotiation",
                "first right.*purchase"
            ],
            "minimum commitment": [
                "minimum commitment", "minimum.*purchase",
                "minimum.*order", "minimum.*volume",
                "guaranteed.*minimum"
            ],
            "volume restriction": [
                "volume.*restrict", "quantity.*limit",
                "maximum.*volume", "cap.*quantity"
            ],
            "post-termination services": [
                "post-termination", "after.*termination",
                "survival", "surviving.*obligation",
                "obligation.*continue.*after"
            ],
            "audit rights": [
                "audit.*right", "right.*audit", "inspection.*right",
                "right.*inspect", "examine.*books.*records",
                "access.*records"
            ],
            "price restrictions": [
                "price.*restrict", "pricing.*restrict",
                "price.*increase.*limit", "price.*adjustment",
                "price.*cap"
            ],
            "governing law": [
                "governing law", "governed by.*laws",
                "choice of law", "applicable law",
                "laws of the state"
            ],
            "jurisdiction": [
                "jurisdiction", "venue", "forum",
                "courts of", "submit.*jurisdiction"
            ],
            "warranty duration": [
                "warranty.*period", "warranty.*duration",
                "warranty.*term", "warranty.*expire",
                "warranted for"
            ],
            "insurance": [
                "insurance", "insured", "policy.*coverage",
                "maintain.*insurance", "proof of insurance"
            ],
            "notice period": [
                "notice.*period", "days.*notice", "written.*notice",
                "advance.*notice", "prior.*notice"
            ],
            "renewal term": [
                "renewal", "renew.*term", "auto.*renew",
                "automatic.*renewal", "option to renew"
            ],
            "cap on liability": [
                "cap.*liability", "liability.*cap",
                "maximum.*liability", "liability.*not.*exceed",
                "total.*liability.*limited"
            ],
            "covenant not to sue": [
                "covenant not to sue", "waive.*right.*sue",
                "release.*claims", "not.*bring.*action"
            ],
            "irrevocable or perpetual license": [
                "irrevocable.*license", "perpetual.*license",
                "permanent.*license", "irrevocable.*right"
            ],
            "license grant": [
                "hereby grants", "license.*grant", "grant.*license",
                "right.*use", "permission.*use", "licensed.*under"
            ],
            "revenue/profit sharing": [
                "revenue.*sharing", "profit.*sharing", "revenue.*split",
                "share.*revenue", "share.*profit", "royalt"
            ],
            "non-disparagement": [
                "non-disparagement", "nondisparagement",
                "not.*disparage", "refrain.*negative.*statement"
            ],
        }


risk_scorer = RiskScorer()
