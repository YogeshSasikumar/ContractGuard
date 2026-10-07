"""
Analysis Route — Additional analysis endpoints.
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ExplanationRequest
from app.services.gemini_explainer import gemini_explainer
from app.services.risk_scorer import risk_scorer

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/explain")
async def explain_clause(request: ExplanationRequest):
    """Generate an AI explanation for a specific clause."""
    explanation = await gemini_explainer.explain_clause(
        request.clause_text,
        request.clause_type,
        request.risk_level
    )
    return explanation


@router.post("/classify")
async def classify_text(text: str):
    """Classify a piece of text using ML models with keyword fallback."""
    from app.services.classifier import classify_clause, is_model_available

    if is_model_available():
        result = classify_clause(text)
        if result.get("clause_type"):
            result["risk_level"] = risk_scorer.get_risk_level(result["clause_type"])
            return result

    # Fallback to keyword
    return risk_scorer.classify_clause_keyword(text)


@router.get("/risk-mapping")
async def get_risk_mapping():
    """Return the complete risk level mapping."""
    return {
        "mapping": risk_scorer.risk_mapping,
        "descriptions": risk_scorer.clause_descriptions
    }
