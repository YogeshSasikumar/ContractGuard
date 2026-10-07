"""
Riskora — FastAPI Backend
CCRAG-based Legal Contract Risk Analysis System
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import upload, cases, analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup, cleanup on shutdown."""
    logger.info("=" * 60)
    logger.info("Riskora Backend Starting...")
    logger.info(f"Deployment mode: {settings.deployment_mode.upper()}")
    logger.info(f"Gemini API: {'Configured' if settings.gemini_api_key else 'Not configured (fallback mode)'}")
    logger.info(f"Upload dir: {settings.upload_dir}")
    logger.info("=" * 60)

    if settings.is_lite_mode:
        # LITE MODE: Skip heavy ML models — use keyword classifier + Gemini only
        logger.info("LITE MODE: Skipping ML model loading (keyword + Gemini only)")
        logger.info("This keeps RAM under 512 MB for free-tier hosting.")
    else:
        # FULL MODE: Load all ML models
        logger.info("FULL MODE: Loading ML models...")

        from app.services.classifier import load_legal_bert, load_bart_mnli
        from app.services.case_matcher import load_embedding_model, case_matcher

        # 1. Legal-BERT (primary classifier)
        load_legal_bert()

        # 2. BART-MNLI (fallback classifier)
        load_bart_mnli()

        # 3. Sentence-transformer (case matching)
        load_embedding_model()

        # 4. Pre-compute case embeddings
        case_matcher.precompute_embeddings()

    from app.services.classifier import is_model_available
    logger.info("=" * 60)
    logger.info(f"ML Models Ready: {is_model_available()}")
    logger.info("Riskora Backend Ready!")
    logger.info("=" * 60)

    yield  # App is running

    logger.info("Riskora shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Riskora",
    description="CCRAG-based Legal Contract Risk Analysis System — Identifies, classifies, and explains risky clauses in legal contracts.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(cases.router)
app.include_router(analysis.router)


@app.get("/")
async def root():
    return {
        "app": "Riskora",
        "version": "2.0.0",
        "description": "CCRAG-based Legal Contract Risk Analysis System",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    from app.services.classifier import is_model_available, _is_legal_bert_loaded, _is_bart_loaded
    from app.services.case_matcher import _is_embedding_loaded

    return {
        "status": "healthy",
        "version": "2.0.0",
        "models": {
            "legal_bert": _is_legal_bert_loaded,
            "bart_mnli": _is_bart_loaded,
            "sentence_transformer": _is_embedding_loaded,
            "any_ml_available": is_model_available(),
        },
        "gemini_configured": bool(settings.gemini_api_key),
    }
