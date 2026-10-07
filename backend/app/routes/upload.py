"""
Upload Route — Async job-based PDF analysis pipeline.
Upload returns immediately with job_id. Processing runs in background.
Frontend polls GET /api/status/{job_id} for results.
"""

import uuid
import time
import json
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.models.schemas import (
    AnalysisResponse, ClauseResult, RiskSummary, CaseMatch,
    TopRiskyClause, GraphStats, ModelHealth, ModelTrace, SystemNovelty,
)
from app.services.pdf_parser import pdf_parser
from app.services.clause_segmenter import clause_segmenter
from app.services.risk_scorer import risk_scorer
from app.services.classifier import classify_batch, classify_clause, is_model_available, CALIBRATION_TEMPERATURE
from app.services.clause_graph import clause_graph
from app.services.gemini_explainer import gemini_explainer
from app.services.case_matcher import case_matcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])

# ── Job Store (in-memory) ──
# { job_id: { status, progress, step, result, error, started_at } }
job_store: dict[str, dict] = {}

# Also keep full analysis data for detail endpoints
analysis_store: dict[str, dict] = {}

# ── Disk Persistence ──
RESULTS_DIR = settings.base_dir / "analysis_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_to_disk(job_id: str, result_data: dict):
    """Persist analysis result as JSON file."""
    try:
        filepath = RESULTS_DIR / f"{job_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result_data, f, default=str)
        logger.info(f"[{job_id}] Saved to disk: {filepath}")
    except Exception as e:
        logger.error(f"[{job_id}] Failed to save to disk: {e}")


def _load_all_from_disk():
    """Load all saved analyses from disk into memory."""
    count = 0
    for filepath in RESULTS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            job_id = filepath.stem
            analysis_store[job_id] = {"response": data}
            job_store[job_id] = {
                "status": "completed",
                "progress": 100,
                "step": "Analysis complete",
                "result": data,
                "error": None,
                "started_at": 0,
                "filename": data.get("document_name", "unknown"),
            }
            count += 1
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
    if count:
        logger.info(f"Loaded {count} previous analyses from disk")


# Load previous results on module import
_load_all_from_disk()


@router.post("/upload")
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a PDF and start background analysis.
    Returns job_id immediately — poll /api/status/{job_id} for results.
    """
    logger.info(f"Upload received: {file.filename} (content_type={file.content_type})")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    job_id = str(uuid.uuid4())[:8]

    # Save file to disk in chunks (handles large files without OOM)
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file.filename)
    file_path = settings.upload_dir / f"{job_id}_{safe_name}"

    try:
        total_size = 0
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                if total_size > 50 * 1024 * 1024:  # 50MB limit
                    f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="File size exceeds 50MB limit.")
                f.write(chunk)
        logger.info(f"[{job_id}] File saved: {file_path} ({total_size} bytes)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] File save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Initialize job
    job_store[job_id] = {
        "status": "processing",
        "progress": 0,
        "step": "Extracting text from PDF...",
        "result": None,
        "error": None,
        "started_at": time.time(),
        "filename": file.filename,
    }

    # Launch background task
    asyncio.create_task(_run_analysis(job_id, file_path, file.filename))

    return {"job_id": job_id, "status": "processing"}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Poll this endpoint for analysis progress and results."""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = job_store[job_id]
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "step": job["step"],
    }

    if job["status"] == "completed":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job["error"]

    return response


async def _run_analysis(job_id: str, file_path, filename: str):
    """Background analysis pipeline. Updates job_store with progress."""
    start_time = time.time()

    def _update(progress: int, step: str):
        job_store[job_id]["progress"] = progress
        job_store[job_id]["step"] = step
        logger.info(f"[{job_id}] {progress}% — {step}")

    try:
        # ── Step 1: Extract text ──
        _update(10, "Extracting text from PDF...")
        pdf_data = pdf_parser.extract_text(file_path)

        if not pdf_data["full_text"].strip():
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["error"] = "Could not extract text. The PDF may be image-based."
            return

        # ── Step 2: Segment clauses ──
        _update(20, "Segmenting clauses...")
        clauses = clause_segmenter.segment(pdf_data["full_text"], pdf_data["pages"])

        if not clauses:
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["error"] = "No meaningful clauses found."
            return

        # ── Step 3: Classify (ML) ──
        _update(30, f"Classifying {len(clauses)} clauses...")
        ml_available = is_model_available()
        classified_clauses = []

        if ml_available:
            clause_texts = [c["text"] for c in clauses]
            # Run ML in executor to not block event loop
            loop = asyncio.get_event_loop()
            ml_results = await loop.run_in_executor(
                None, lambda: classify_batch(clause_texts, batch_size=8)
            )

            for clause, ml_result in zip(clauses, ml_results):
                clause_type = ml_result.get("clause_type")
                if clause_type and clause_type != "None":
                    risk_level = risk_scorer.get_risk_level(clause_type)
                    classified_clauses.append({
                        **clause,
                        "clause_type": clause_type,
                        "risk_level": risk_level,
                        "confidence": ml_result.get("confidence", 0.5),
                        "model": ml_result.get("model", "unknown"),
                    })
                else:
                    kw_result = risk_scorer.classify_clause_keyword(clause["text"])
                    classified_clauses.append({**clause, **kw_result})
        else:
            for clause in clauses:
                kw_result = risk_scorer.classify_clause_keyword(clause["text"])
                classified_clauses.append({**clause, **kw_result})

        _update(50, "Building clause relationship graph...")

        # ── Step 4: Graph + centrality ──
        graph_stats_data = {"nodes": 0, "edges": 0, "max_centrality": 0.0, "components": 0}
        try:
            graph_result = clause_graph.build_graph(classified_clauses)
            centrality_scores = graph_result.get("centrality", {})
            graph_stats_data = graph_result.get("stats", graph_stats_data)
        except Exception as e:
            logger.error(f"[{job_id}] Graph failed: {e}")
            centrality_scores = {}

        for clause_data in classified_clauses:
            cid = clause_data.get("id", 0)
            centrality = centrality_scores.get(cid, 0.0)
            clause_data["centrality"] = round(centrality, 4)
            clause_data["risk_score"] = risk_scorer.compute_clause_risk_score(
                clause_data.get("confidence", 0.5), centrality
            )

        # ── Step 5: AI Explanations (parallel) ──
        _update(60, "Generating AI explanations...")
        try:
            explanations = await gemini_explainer.explain_batch(classified_clauses)
            for clause_data, explanation in zip(classified_clauses, explanations):
                if isinstance(explanation, dict):
                    clause_data["explanation"] = explanation.get("explanation", "")
                    clause_data["suggested_rewrite"] = explanation.get("suggested_rewrite", "")
                    clause_data["risks"] = explanation.get("risks", [])
                    clause_data["recommendations"] = explanation.get("recommendations", [])
                else:
                    clause_data.setdefault("explanation", "")
                    clause_data.setdefault("risks", [])
                    clause_data.setdefault("recommendations", [])
                    clause_data.setdefault("suggested_rewrite", "")
        except Exception as e:
            logger.error(f"[{job_id}] Explanation batch failed: {e}")
            for clause_data in classified_clauses:
                clause_data.setdefault("explanation", "")
                clause_data.setdefault("risks", [])
                clause_data.setdefault("recommendations", [])
                clause_data.setdefault("suggested_rewrite", "")

        # ── Step 6: Case matching ──
        _update(80, "Matching case law...")
        for clause_data in classified_clauses:
            try:
                matching_cases = case_matcher.find_matching_cases(
                    clause_text=clause_data["text"][:500],
                    clause_type=clause_data["clause_type"],
                    risk_level=clause_data.get("risk_level"),
                    limit=2,
                )
                clause_data["related_cases"] = matching_cases
            except Exception:
                clause_data["related_cases"] = []

        # ── Step 7: Build response ──
        _update(90, "Finalizing results...")
        risk_summary = risk_scorer.compute_overall_risk(classified_clauses)

        from app.services.classifier import _is_legal_bert_loaded, _is_bart_loaded
        from app.services.case_matcher import _is_embedding_loaded

        model_health = ModelHealth(
            legal_bert=_is_legal_bert_loaded,
            bart_mnli=_is_bart_loaded,
            sentence_transformer=_is_embedding_loaded,
            gemini_available=bool(settings.gemini_api_key),
        )

        clause_results = []
        for c in classified_clauses:
            clause_results.append(ClauseResult(
                id=c["id"],
                text=c["text"][:500],
                clause_type=c.get("clause_type", "Uncategorized"),
                risk_level=c.get("risk_level", "LOW"),
                confidence=c.get("confidence", 0.0),
                centrality=c.get("centrality", 0.0),
                risk_score=c.get("risk_score", 0.0),
                model_used=c.get("model", "keyword"),
                explanation=c.get("explanation", ""),
                suggested_rewrite=c.get("suggested_rewrite", ""),
                risks=c.get("risks", []),
                recommendations=c.get("recommendations", []),
                related_cases=[CaseMatch(**rc) if isinstance(rc, dict) else rc for rc in c.get("related_cases", [])],
                page_number=c.get("page_number"),
                section_heading=c.get("section_heading"),
                model_trace=ModelTrace(
                    model_used=c.get("model", "keyword"),
                    calibration_applied=True,
                    graph_used=True,
                    temperature=CALIBRATION_TEMPERATURE,
                ),
            ))

        processing_time = round(time.time() - start_time, 2)
        top_risky = [TopRiskyClause(**trc) for trc in risk_summary.get("top_risky_clauses", [])]

        response = AnalysisResponse(
            document_name=filename,
            total_pages=pdf_data["total_pages"],
            risk_summary=RiskSummary(
                total_clauses=risk_summary["total_clauses"],
                high_risk=risk_summary["high_risk"],
                medium_risk=risk_summary["medium_risk"],
                low_risk=risk_summary["low_risk"],
                overall_risk_score=risk_summary["overall_risk_score"],
                risk_distribution=risk_summary["risk_distribution"],
                top_risky_clauses=top_risky,
                graph_stats=GraphStats(**graph_stats_data),
            ),
            clauses=clause_results,
            processing_time=processing_time,
            model_health=model_health,
            system_novelty=SystemNovelty(),
        )

        # Store results
        result_data = response.model_dump()
        analysis_store[job_id] = {
            "response": result_data,
            "full_clauses": classified_clauses,
            "pdf_metadata": pdf_data["metadata"],
        }

        # Persist to disk
        _save_to_disk(job_id, result_data)

        # Mark job complete
        _update(100, "Analysis complete")
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = result_data

        logger.info(f"[{job_id}] DONE in {processing_time}s — {len(clauses)} clauses")

    except Exception as e:
        logger.exception(f"[{job_id}] Analysis failed: {e}")
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)


@router.get("/history")
async def list_analyses():
    """List all previously analyzed contracts."""
    history = []
    for jid, job in job_store.items():
        if job["status"] != "completed" or not job.get("result"):
            continue
        r = job["result"]
        rs = r.get("risk_summary", {})
        history.append({
            "job_id": jid,
            "document_name": r.get("document_name", "Unknown"),
            "total_pages": r.get("total_pages", 0),
            "total_clauses": rs.get("total_clauses", 0),
            "high_risk": rs.get("high_risk", 0),
            "medium_risk": rs.get("medium_risk", 0),
            "low_risk": rs.get("low_risk", 0),
            "overall_risk_score": rs.get("overall_risk_score", 0),
            "processing_time": r.get("processing_time", 0),
        })
    return {"analyses": history, "total": len(history)}


@router.get("/analysis/{doc_id}")
async def get_analysis(doc_id: str):
    """Retrieve a previous analysis result."""
    if doc_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis_store[doc_id]["response"]


@router.get("/analysis/{doc_id}/clauses/{clause_id}")
async def get_clause_detail(doc_id: str, clause_id: int):
    """Get full details for a specific clause."""
    if doc_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    clauses = analysis_store[doc_id].get("full_clauses", [])
    for clause in clauses:
        if clause.get("id") == clause_id:
            return clause
    raise HTTPException(status_code=404, detail="Clause not found.")
