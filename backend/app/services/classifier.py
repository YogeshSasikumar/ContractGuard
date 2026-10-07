"""
Dual-Model Clause Classifier
Primary: Legal-BERT (nlpaueb/legal-bert-base-uncased) — cosine similarity classification
Fallback: BART-MNLI (facebook/bart-large-mnli) — zero-shot classification
Final Fallback: Keyword matching (from risk_scorer)

Includes temperature scaling for confidence calibration.
"""

import logging
import math
import numpy as np
from typing import Optional

try:
    import torch
    from torch.nn.functional import softmax
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


logger = logging.getLogger(__name__)

# Module-level state
_legal_bert_model = None
_legal_bert_tokenizer = None
_bart_pipeline = None
_label_embeddings = None
_label_names = None
_is_legal_bert_loaded = False
_is_bart_loaded = False

# Confidence threshold: below this, fall back to BART
# After temperature scaling, ~0.10+ indicates a meaningful classification
LEGAL_BERT_CONFIDENCE_THRESHOLD = 0.10

# Temperature for confidence calibration
# T > 1.0 softens overconfident predictions; T=1.5 is a good default
CALIBRATION_TEMPERATURE = 1.5

# Clause type labels with descriptions for embedding-based matching
CLAUSE_LABELS = {
    "Indemnification": "indemnification hold harmless defend compensate losses damages",
    "Limitation of Liability": "limitation of liability limit liable aggregate liability shall not exceed",
    "Uncapped Liability": "unlimited liability uncapped no limit without limitation damages",
    "IP Ownership Assignment": "intellectual property assign work for hire all rights title interest patent copyright",
    "Non-Compete": "non-compete covenant not to compete competitive activity refrain competing",
    "Exclusivity": "exclusive exclusivity sole right sole provider exclusive license agreement",
    "Most Favored Nation": "most favored nation mfn no less favorable pricing terms",
    "Anti-Assignment": "anti-assignment shall not assign prohibited without consent transfer",
    "Change of Control": "change of control merger acquisition controlling interest ownership transfer",
    "Liquidated Damages": "liquidated damages predetermined stipulated agreed damage amount penalty",
    "Termination For Convenience": "termination for convenience without cause any reason no reason at any time",
    "Non-Solicitation": "non-solicitation shall not solicit refrain soliciting recruit employees",
    "Rofr/Rofo/Rofn": "right of first refusal offer negotiation first right purchase",
    "Minimum Commitment": "minimum commitment purchase order volume guaranteed minimum",
    "Volume Restriction": "volume restriction quantity limit maximum cap",
    "Post-Termination Services": "post-termination after termination survival surviving obligation continue",
    "Audit Rights": "audit right inspection examine books records access review",
    "Price Restrictions": "price restriction pricing increase limit adjustment cap",
    "Governing Law": "governing law governed by laws choice of law applicable law state",
    "Jurisdiction": "jurisdiction venue forum courts submit exclusive jurisdiction",
    "Warranty Duration": "warranty period duration term expire warranted",
    "Insurance": "insurance insured policy coverage maintain proof",
    "Notice Period": "notice period days written advance prior notification",
    "Renewal Term": "renewal renew term automatic option extend",
    "Cap On Liability": "cap liability maximum total limited aggregate ceiling",
    "Covenant Not To Sue": "covenant not to sue waive right release claims action",
    "Irrevocable Or Perpetual License": "irrevocable perpetual permanent license right grant",
    "License Grant": "hereby grants license grant right use permission licensed under",
    "Revenue/Profit Sharing": "revenue profit sharing split share royalty percentage",
    "Non-Disparagement": "non-disparagement not disparage refrain negative statement criticism",
    "Source Code Escrow": "source code escrow deposit release access contingency",
    "Third Party Beneficiary": "third party beneficiary rights enforce benefit intended",
    "Joint IP Ownership": "joint ownership intellectual property shared rights co-owned",
    "Affiliate License": "affiliate subsidiary license grant related entity rights",
    "Competitive Restriction Exception": "exception competitive restriction carve-out permitted allowed",
}


def _mean_pooling(model_output, attention_mask):
    """Mean pooling over token embeddings, weighted by attention mask."""
    token_embeddings = model_output[0]  # First element = token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def load_legal_bert() -> bool:
    """Load Legal-BERT for embedding-based classification."""
    global _legal_bert_model, _legal_bert_tokenizer, _label_embeddings, _label_names, _is_legal_bert_loaded

    if not _TORCH_AVAILABLE:
        logger.info("Skipping Legal-BERT (torch not installed — lite mode)")
        return False

    try:
        from transformers import AutoTokenizer, AutoModel

        logger.info("Loading Legal-BERT (nlpaueb/legal-bert-base-uncased)...")
        _legal_bert_tokenizer = AutoTokenizer.from_pretrained(
            "nlpaueb/legal-bert-base-uncased"
        )
        _legal_bert_model = AutoModel.from_pretrained(
            "nlpaueb/legal-bert-base-uncased"
        )
        _legal_bert_model.eval()

        # Move to GPU if available
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _legal_bert_model = _legal_bert_model.to(device)
        logger.info(f"Legal-BERT loaded on {device}")

        # Pre-compute label embeddings
        _label_names = list(CLAUSE_LABELS.keys())
        label_texts = list(CLAUSE_LABELS.values())

        encoded = _legal_bert_tokenizer(
            label_texts, padding=True, truncation=True, max_length=128, return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            output = _legal_bert_model(**encoded)
            _label_embeddings = _mean_pooling(output, encoded["attention_mask"])
            # Normalize
            _label_embeddings = torch.nn.functional.normalize(_label_embeddings, p=2, dim=1)

        _is_legal_bert_loaded = True
        logger.info(f"Legal-BERT ready — {len(_label_names)} clause labels embedded")
        return True

    except Exception as e:
        logger.error(f"Failed to load Legal-BERT: {e}")
        _is_legal_bert_loaded = False
        return False


def load_bart_mnli() -> bool:
    """Load BART-MNLI for zero-shot classification (fallback)."""
    global _bart_pipeline, _is_bart_loaded

    if not _TORCH_AVAILABLE:
        logger.info("Skipping BART-MNLI (torch not installed — lite mode)")
        return False

    try:
        from transformers import pipeline

        logger.info("Loading BART-MNLI zero-shot pipeline...")
        _bart_pipeline = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if torch.cuda.is_available() else -1,
        )
        _is_bart_loaded = True
        logger.info("BART-MNLI loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to load BART-MNLI: {e}")
        _is_bart_loaded = False
        return False


def is_model_available() -> bool:
    """Check if at least one ML model is loaded."""
    return _is_legal_bert_loaded or _is_bart_loaded


def calibrate_confidence(raw_scores: np.ndarray, temperature: float = CALIBRATION_TEMPERATURE) -> np.ndarray:
    """
    Apply temperature scaling to raw similarity scores.
    
    Temperature scaling converts raw cosine similarities into calibrated
    probabilities using softmax(scores / T). T > 1 softens the distribution,
    preventing overconfident predictions.
    
    Args:
        raw_scores: Raw cosine similarity scores (can be negative)
        temperature: Scaling factor. Higher = softer distribution.
    
    Returns:
        Calibrated probability distribution that sums to 1.0
    """
    # Shift scores to be non-negative before scaling
    shifted = raw_scores - raw_scores.min() + 1e-6
    scaled = shifted / temperature
    # Softmax for proper probability distribution
    exp_scores = np.exp(scaled - np.max(scaled))  # numerical stability
    probabilities = exp_scores / exp_scores.sum()
    return probabilities


def _cosine_to_confidence(raw_scores: np.ndarray) -> tuple[int, float]:
    """
    Convert raw cosine similarity scores to a calibrated confidence value
    using temperature scaling.
    
    Returns:
        (best_index, calibrated_confidence)
    """
    # Apply temperature scaling to get calibrated probabilities
    calibrated = calibrate_confidence(raw_scores, CALIBRATION_TEMPERATURE)
    
    best_idx = int(np.argmax(calibrated))
    confidence = float(calibrated[best_idx])

    # Clamp to [0, 1] (should already be, but safety)
    confidence = max(0.0, min(1.0, confidence))

    return best_idx, round(confidence, 4)


def _classify_legal_bert(text: str) -> Optional[dict]:
    """Classify using Legal-BERT embeddings + cosine similarity."""
    if not _is_legal_bert_loaded:
        return None

    try:
        device = next(_legal_bert_model.parameters()).device

        # Encode clause text
        encoded = _legal_bert_tokenizer(
            text, padding=True, truncation=True, max_length=256, return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            output = _legal_bert_model(**encoded)
            clause_embedding = _mean_pooling(output, encoded["attention_mask"])
            clause_embedding = torch.nn.functional.normalize(clause_embedding, p=2, dim=1)

        # Cosine similarity against all labels
        similarities = torch.mm(clause_embedding, _label_embeddings.t()).squeeze(0)
        raw_scores = similarities.cpu().numpy()

        # Apply temperature-calibrated confidence
        calibrated = calibrate_confidence(raw_scores, CALIBRATION_TEMPERATURE)
        best_idx, confidence = _cosine_to_confidence(raw_scores)

        # Get top 3 using calibrated probabilities
        top_indices = np.argsort(calibrated)[::-1][:3]
        top_results = [
            {"clause_type": _label_names[i], "confidence": round(float(calibrated[i]), 4)}
            for i in top_indices
        ]

        return {
            "clause_type": _label_names[best_idx],
            "confidence": confidence,
            "raw_similarity": round(float(raw_scores[best_idx]), 4),
            "model": "legal-bert",
            "top_predictions": top_results,
        }

    except Exception as e:
        logger.error(f"Legal-BERT inference failed: {e}")
        return None


def _classify_bart(text: str) -> Optional[dict]:
    """Classify using BART-MNLI zero-shot pipeline with reduced label set for speed."""
    if not _is_bart_loaded:
        return None

    try:
        # Use top 8 most critical labels for speed (35 labels = 35 forward passes = slow)
        BART_FAST_LABELS = [
            "Indemnification", "Limitation of Liability", "Non-Compete",
            "Termination For Convenience", "IP Ownership Assignment",
            "Governing Law", "Non-Solicitation", "Exclusivity",
        ]
        result = _bart_pipeline(
            text[:512],  # Truncate for speed
            candidate_labels=BART_FAST_LABELS,
            multi_label=False,
        )

        confidence = float(result["scores"][0])

        top_results = [
            {"clause_type": result["labels"][i], "confidence": round(float(result["scores"][i]), 4)}
            for i in range(min(3, len(result["labels"])))
        ]

        return {
            "clause_type": result["labels"][0],
            "confidence": round(confidence, 4),
            "model": "bart-mnli",
            "top_predictions": top_results,
        }

    except Exception as e:
        logger.error(f"BART-MNLI inference failed: {e}")
        return None


def classify_clause(text: str) -> dict:
    """
    Dual-model classification with intelligent fallback.

    Priority: Legal-BERT → BART-MNLI → Keyword (via risk_scorer)

    Returns:
        dict with: clause_type, confidence, model, top_predictions,
                   legal_bert_result, bart_result (for comparison)
    """
    legal_bert_result = None
    bart_result = None

    # Try Legal-BERT first (primary)
    if _is_legal_bert_loaded:
        legal_bert_result = _classify_legal_bert(text)

    # Check if Legal-BERT is confident enough
    if legal_bert_result and legal_bert_result["confidence"] >= LEGAL_BERT_CONFIDENCE_THRESHOLD:
        selected = legal_bert_result
    else:
        # Fall back to BART-MNLI
        if _is_bart_loaded:
            bart_result = _classify_bart(text)
        
        if bart_result:
            selected = bart_result
        elif legal_bert_result:
            # Use Legal-BERT even with low confidence if BART failed
            selected = legal_bert_result
        else:
            # Both models failed — return None (upload.py will use keyword fallback)
            return {
                "clause_type": None,
                "confidence": 0.0,
                "model": "none",
                "top_predictions": [],
                "legal_bert_result": None,
                "bart_result": None,
            }

    # Attach both results for evaluation
    selected["legal_bert_result"] = legal_bert_result
    selected["bart_result"] = bart_result

    return selected


def classify_batch(texts: list[str], batch_size: int = 8) -> list[dict]:
    """
    Classify multiple clauses efficiently.
    Uses batched Legal-BERT encoding for speed.
    """
    import time
    total = len(texts)
    logger.info(f"Batch classification starting: {total} clauses")
    t0 = time.time()

    if not _is_legal_bert_loaded:
        # Fall back to individual classification
        results = []
        for i, t in enumerate(texts):
            results.append(classify_clause(t))
            if (i + 1) % 5 == 0:
                logger.info(f"  Classified {i+1}/{total} (no Legal-BERT, using fallback)")
        return results

    results = []
    device = next(_legal_bert_model.parameters()).device
    bart_count = 0

    for i in range(0, total, batch_size):
        batch_texts = texts[i : i + batch_size]

        try:
            encoded = _legal_bert_tokenizer(
                batch_texts, padding=True, truncation=True, max_length=256, return_tensors="pt"
            ).to(device)

            with torch.no_grad():
                output = _legal_bert_model(**encoded)
                embeddings = _mean_pooling(output, encoded["attention_mask"])
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            # Cosine similarity for entire batch at once
            similarities = torch.mm(embeddings, _label_embeddings.t()).cpu().numpy()

            for j, raw_scores in enumerate(similarities):
                # Apply temperature-calibrated confidence
                calibrated = calibrate_confidence(raw_scores, CALIBRATION_TEMPERATURE)
                best_idx = int(np.argmax(calibrated))
                confidence = round(float(calibrated[best_idx]), 4)

                top_indices = np.argsort(calibrated)[::-1][:3]
                top_results = [
                    {"clause_type": _label_names[k], "confidence": round(float(calibrated[k]), 4)}
                    for k in top_indices
                ]

                lb_result = {
                    "clause_type": _label_names[best_idx],
                    "confidence": confidence,
                    "raw_similarity": round(float(raw_scores[best_idx]), 4),
                    "model": "legal-bert",
                    "top_predictions": top_results,
                }

                if confidence >= LEGAL_BERT_CONFIDENCE_THRESHOLD:
                    lb_result["legal_bert_result"] = lb_result.copy()
                    lb_result["bart_result"] = None
                    results.append(lb_result)
                else:
                    # Fall back to BART for this clause
                    bart_count += 1
                    bart_res = _classify_bart(batch_texts[j])
                    if bart_res:
                        bart_res["legal_bert_result"] = lb_result.copy()
                        bart_res["bart_result"] = bart_res.copy()
                        results.append(bart_res)
                    else:
                        lb_result["legal_bert_result"] = lb_result.copy()
                        lb_result["bart_result"] = None
                        results.append(lb_result)

        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            for text in batch_texts:
                results.append(classify_clause(text))

        done = min(i + batch_size, total)
        elapsed = round(time.time() - t0, 1)
        logger.info(f"  Classified {done}/{total} clauses ({elapsed}s, {bart_count} BART fallbacks)")

    logger.info(f"Batch classification done: {total} clauses in {round(time.time()-t0,1)}s ({bart_count} used BART)")
    return results
