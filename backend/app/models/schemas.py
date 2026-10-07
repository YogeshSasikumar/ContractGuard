from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CaseMatch(BaseModel):
    """A matched legal case returned with a clause."""
    id: Optional[int] = None
    case_name: str = ""
    year: Optional[int] = None
    clause_type: str = ""
    risk_level: Optional[str] = None
    parties: Optional[str] = None
    summary: str = ""
    outcome: Optional[str] = None
    financial_impact: Optional[str] = None
    lesson: Optional[str] = None
    source: Optional[str] = None
    similarity_score: Optional[float] = None


class ModelTrace(BaseModel):
    """Trace of which models/features were used for this clause — novelty proof."""
    model_used: str = "keyword"
    calibration_applied: bool = True
    graph_used: bool = True
    temperature: float = 1.5


class ClauseResult(BaseModel):
    id: int
    text: str
    clause_type: str
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    centrality: Optional[float] = None
    risk_score: Optional[float] = None
    model_used: Optional[str] = None
    explanation: Optional[str] = ""
    suggested_rewrite: Optional[str] = ""
    risks: list[str] = []
    recommendations: list[str] = []
    related_cases: list[CaseMatch] = []
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    model_trace: Optional[ModelTrace] = None


class TopRiskyClause(BaseModel):
    """Compact representation of a top risky clause for the summary."""
    id: int
    clause_type: str
    risk_level: str
    risk_score: float
    confidence: float


class GraphStats(BaseModel):
    """Clause graph statistics."""
    nodes: int = 0
    edges: int = 0
    max_centrality: float = 0.0
    components: int = 0


class ModelHealth(BaseModel):
    """Status of ML models used during analysis."""
    legal_bert: bool = False
    bart_mnli: bool = False
    sentence_transformer: bool = False
    gemini_available: bool = False


class SystemNovelty(BaseModel):
    """Proof of system differentiation from generic LLMs — for viva defense."""
    deterministic_output: bool = True
    structured_classification: bool = True
    calibrated_confidence: bool = True
    graph_based_prioritization: bool = True
    dual_model_fallback: bool = True
    description: str = (
        "Unlike ChatGPT or Gemini, this system uses deterministic ML classification "
        "(Legal-BERT + BART-MNLI) with temperature-calibrated confidence scores, "
        "NetworkX-based clause relationship graphs for structural risk prioritization, "
        "and semantic case law matching via sentence embeddings. The same input always "
        "produces the same classification and risk score. LLMs are used only for "
        "human-readable explanations, not for classification or scoring."
    )


class RiskSummary(BaseModel):
    total_clauses: int
    high_risk: int
    medium_risk: int
    low_risk: int
    overall_risk_score: float = Field(ge=0.0, le=100.0)
    risk_distribution: dict[str, float]
    top_risky_clauses: list[TopRiskyClause] = []
    graph_stats: Optional[GraphStats] = None


class AnalysisResponse(BaseModel):
    document_name: str
    total_pages: int
    risk_summary: RiskSummary
    clauses: list[ClauseResult]
    processing_time: float
    model_health: Optional[ModelHealth] = None
    system_novelty: Optional[SystemNovelty] = None


class CaseStudy(BaseModel):
    id: int
    case_name: str
    year: int
    clause_type: str
    risk_level: RiskLevel
    parties: str
    summary: str
    outcome: str
    financial_impact: Optional[str] = None
    lesson: str
    source: Optional[str] = None


class UploadResponse(BaseModel):
    message: str
    document_id: str
    filename: str


class ExplanationRequest(BaseModel):
    clause_text: str
    clause_type: str
    risk_level: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str
