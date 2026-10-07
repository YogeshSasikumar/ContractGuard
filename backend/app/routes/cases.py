"""
Cases Route — Serves the curated case knowledge base.
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.case_matcher import case_matcher

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("/")
async def get_all_cases(
    risk_level: str = Query(None, description="Filter by risk level: HIGH, MEDIUM, LOW"),
    clause_type: str = Query(None, description="Filter by clause type")
):
    """Get all cases from the knowledge base with optional filters."""
    cases = case_matcher.get_all_cases()
    
    if risk_level:
        cases = [c for c in cases if c.get("risk_level", "").upper() == risk_level.upper()]
    
    if clause_type:
        clause_lower = clause_type.lower()
        cases = [c for c in cases if clause_lower in c.get("clause_type", "").lower()]
    
    return {"cases": cases, "total": len(cases)}


@router.get("/{case_id}")
async def get_case(case_id: int):
    """Get a specific case by ID."""
    case = case_matcher.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.get("/match/{clause_type}")
async def match_cases(
    clause_type: str,
    risk_level: str = Query(None),
    limit: int = Query(3, ge=1, le=10)
):
    """Find cases matching a specific clause type."""
    matches = case_matcher.find_matching_cases(clause_type, risk_level, limit)
    return {"matches": matches, "total": len(matches)}
