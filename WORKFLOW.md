# Riskora — System Workflow & Architecture

A complete breakdown of how the system works, from the moment you upload a contract to viewing the final risk analysis.

---

## High-Level Pipeline

```
📄 PDF Upload → 📝 Text Extraction → ✂️ Clause Segmentation → 🧠 Classification → ⚖️ Risk Scoring → 💡 AI Explanation → 📊 Dashboard
```

---

## Phase 1: Document Ingestion

### What happens when you upload a PDF?

When a user drags and drops a PDF file into the upload zone, the file is sent to the backend via a `POST /api/upload` request as multipart form data.

**Technology:** `FastAPI` + `python-multipart`

```
User uploads contract.pdf (up to 50MB)
        │
        ▼
Backend saves file to /uploads/ directory
with a unique document ID (e.g., "a4f2c9e1")
```

---

## Phase 2: Text Extraction

### Model/Tool: PyMuPDF (fitz)

PyMuPDF is a high-performance PDF parsing library. It reads the PDF page by page and extracts raw text content.

**What it does:**
1. Opens the PDF file
2. Iterates through every page
3. Extracts text from each page using `page.get_text("text")`
4. Cleans the extracted text:
   - Removes null characters
   - Fixes hyphenated line breaks (e.g., `indem-\nnify` → `indemnify`)
   - Collapses excessive whitespace and blank lines
5. Returns the full document text + page-level text mapping

**Output:**
```
{
  "full_text": "This Agreement is entered into by...",
  "pages": [
    { "page_number": 1, "text": "This Agreement...", "char_count": 2450 },
    { "page_number": 2, "text": "Section 3...", "char_count": 3120 },
    ...
  ],
  "total_pages": 45
}
```

> **Limitation:** This only works on text-based PDFs. Scanned/image PDFs would need OCR (Tesseract) — not yet implemented.

---

## Phase 3: Clause Segmentation

### Algorithm: Rule-Based Section Splitting

Contracts are structured documents. This phase splits the full text into individual clauses (the smallest meaningful legal unit).

**How it works — 3-step process:**

#### Step 1: Split by Section Headings
The segmenter uses **regular expressions** to detect section boundaries:
- Numbered sections: `"1."`, `"1.1"`, `"Section 5"`, `"Article III"`
- Uppercase headings: `"INDEMNIFICATION"`, `"LIMITATION OF LIABILITY"`
- Lettered subsections: `"(a)"`, `"(b)"`, `"(i)"`, `"(ii)"`

```
Full Contract Text
    │
    ├── Section 1: DEFINITIONS ─────────── Clause 1
    ├── Section 2: LICENSE GRANT ────────── Clause 2
    ├── Section 3: INDEMNIFICATION ──────── Clause 3
    ├── Section 4: LIMITATION OF LIABILITY  Clause 4
    └── ...
```

#### Step 2: Split Long Sections
If any section is longer than 2,000 characters, it's further split by paragraph breaks (`\n\n`). This ensures each clause is a manageable chunk of text.

#### Step 3: Filter & Assign Metadata
- Clauses shorter than 50 characters are discarded (not meaningful)
- Each clause gets a page number (by matching text against page-level data)
- Each clause gets its section heading

**Output:**
```
[
  {
    "id": 1,
    "text": "The Licensee shall indemnify and hold harmless...",
    "section_heading": "Indemnification",
    "page_number": 12
  },
  {
    "id": 2,
    "text": "In no event shall either party be liable for...",
    "section_heading": "Limitation Of Liability",
    "page_number": 15
  },
  ...
]
```

---

## Phase 4: Clause Classification

### Algorithm: Keyword-Based Pattern Matching (Rule-Based)
*(Will be upgraded to Legal-BERT in Phase 3 of development)*

Each clause is classified into one of **41 clause types** from the CUAD taxonomy. This is done using keyword pattern matching.

**How it works:**

For each clause, the system checks its text against keyword lists for every clause type:

```
Clause Text: "The Licensee shall indemnify and hold harmless the Licensor..."

Keyword Matching:
  ├── "indemnification" keywords: ["indemnif", "hold harmless", "defend and indemnify"]
  │     → MATCH: "indemnif" found ✓, "hold harmless" found ✓
  │     → Score: 2/5 = 0.40
  │
  ├── "non-compete" keywords: ["non-compete", "not compete", ...]
  │     → No matches
  │
  └── ... (checks all 41 types)

Winner: "Indemnification" (highest score)
Confidence: min(0.40 × 2.5, 0.95) = 0.95
```

**Key clause types detected (41 total):**

| Category | Examples |
|----------|----------|
| Liability | Indemnification, Limitation of Liability, Uncapped Liability, Cap on Liability |
| IP & Rights | IP Ownership Assignment, License Grant, Irrevocable License |
| Competition | Non-Compete, Exclusivity, Non-Solicitation, Most Favored Nation |
| Control | Change of Control, Anti-Assignment, Termination for Convenience |
| Financial | Liquidated Damages, Minimum Commitment, Price Restrictions, Revenue Sharing |
| Standard | Governing Law, Jurisdiction, Warranty Duration, Notice Period, Renewal |

### Future Upgrade: Legal-BERT + LoRA

Once trained, the classification will use:

- **Model:** `nlpaueb/legal-bert-base-uncased` — a BERT model pre-trained on 12GB of legal text (legislation, court cases, contracts)
- **Fine-tuning method:** LoRA (Low-Rank Adaptation) — only trains ~0.5% of parameters, making it feasible on a 4-6GB GPU
- **Training data:** CUAD dataset (510 contracts, 13,000+ annotations)
- **Output:** Probability distribution over 41 clause types (multi-label)

---

## Phase 5: Risk Scoring

### Algorithm: Rule-Based Risk Taxonomy

After classification, each clause type is mapped to a risk level using a predefined taxonomy. This mapping is stored in `risk_mapping.json`.

```
Clause Type ──── Risk Mapping ──── Risk Level

"Indemnification"         →   🔴 HIGH
"Limitation of Liability" →   🔴 HIGH
"Non-Compete"             →   🔴 HIGH
"Termination for Conv."   →   🟡 MEDIUM
"Audit Rights"            →   🟡 MEDIUM
"Governing Law"           →   🟢 LOW
"Notice Period"           →   🟢 LOW
```

**Risk Level Definitions:**

| Level | Meaning | Clause Count |
|-------|---------|-------------|
| 🔴 **HIGH** | Can cause significant financial loss, IP theft, or operational damage. Requires legal review before signing. | 15 types |
| 🟡 **MEDIUM** | Creates restrictions that are negotiable. Should be reviewed but common in contracts. | 13 types |
| 🟢 **LOW** | Standard contractual language with minimal risk. Generally safe. | 13 types |

### Overall Risk Score Calculation

```
Risk Score = ( (HIGH × 1.0) + (MEDIUM × 0.5) + (LOW × 0.1) ) / Total Clauses × 100

Example:
  5 HIGH + 8 MEDIUM + 12 LOW clauses
  = (5×1.0 + 8×0.5 + 12×0.1) / 25 × 100
  = (5 + 4 + 1.2) / 25 × 100
  = 40.8 / 100
  = 40.8% Risk Score → MEDIUM overall
```

---

## Phase 6: AI Explanation Generation

### Model: Google Gemini 2.0 Flash (Free Tier)

For every HIGH and MEDIUM risk clause, the system calls Google's Gemini API to generate a human-readable analysis.

**What it generates:**
1. **Plain-English Explanation** — What the clause means, avoiding legal jargon
2. **Key Risks** — Specific dangers this clause creates
3. **Recommendations** — What to negotiate or change
4. **Suggested Rewrite** — A more balanced version of the clause

**Prompt Engineering:**

The system sends a structured prompt to Gemini:

```
You are a senior legal risk analyst. Analyze this contract clause:

Clause Type: Indemnification
Risk Level: HIGH
Clause Text: "The Licensee shall indemnify and hold harmless..."

Provide:
1. EXPLANATION (2-3 sentences, plain English)
2. KEY RISKS (bullet points)
3. RECOMMENDATIONS (bullet points)
4. SUGGESTED REWRITE (balanced version)
```

**Configuration:**
- Temperature: `0.3` (low creativity — we want factual, consistent output)
- Max tokens: `1024`
- Top-p: `0.8`

**Fallback Mode:** If no Gemini API key is configured, the system uses template-based explanations (pre-written descriptions per clause type).

---

## Phase 7: Case Law Matching

### Algorithm: Keyword + Risk Level Matching

Each classified clause is matched against a **curated knowledge base of 25 real legal cases**. This helps users understand real-world consequences.

**Matching Logic:**
1. **Exact match** (score: 1.0) — Clause type matches case's clause type exactly
2. **Partial match** (score: 0.8) — Clause type is a substring of case's type or vice versa
3. **Risk level fallback** (score: 0.3) — Same risk level but different clause type

```
Clause: "Indemnification" (HIGH)
    │
    ├── Exact Match: Enron Corp. Collapse (Indemnification) → Score 1.0
    ├── Exact Match: Theranos Investor Fraud (Indemnification) → Score 1.0
    ├── Exact Match: Boeing 737 MAX (Indemnification) → Score 1.0
    └── Returns top 2 matches
```

**Knowledge Base:** 25 cases covering:
- Enron, WeWork, Theranos, Boeing, Uber/Waymo, ZeniMax/Oculus
- $74B in total documented financial impact
- Cases from 2001–2024
- Each with: parties, summary, outcome, financial impact, legal source, and lesson learned

---

## Phase 8: Response & Dashboard

### Final Output Structure

The backend returns a structured JSON response:

```json
{
  "document_name": "vendor_agreement.pdf",
  "total_pages": 45,
  "processing_time": 8.3,
  "risk_summary": {
    "total_clauses": 25,
    "high_risk": 5,
    "medium_risk": 8,
    "low_risk": 12,
    "overall_risk_score": 40.8,
    "risk_distribution": { "HIGH": 20.0, "MEDIUM": 32.0, "LOW": 48.0 }
  },
  "clauses": [
    {
      "id": 1,
      "text": "The Licensee shall indemnify...",
      "clause_type": "Indemnification",
      "risk_level": "HIGH",
      "confidence": 0.95,
      "explanation": "This clause requires you to...",
      "suggested_rewrite": "Both parties shall mutually...",
      "page_number": 12,
      "section_heading": "Indemnification"
    }
  ]
}
```

### Dashboard Visualization

The React frontend renders the results as:

| Component | What It Shows |
|-----------|--------------|
| **Stats Grid** | 4 cards: Pages Analyzed, High/Medium/Low risk counts |
| **Donut Chart** | Visual ratio of HIGH vs MEDIUM vs LOW clauses (Recharts) |
| **Risk Bars** | Horizontal percentage bars per risk level |
| **Clause List** | Filterable, sortable list of all clauses with risk badges |
| **Detail Panel** | Slide-in panel with full text, explanation, risks, rewrite, and related cases |

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER UPLOADS PDF                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: TEXT EXTRACTION                                       │
│  Tool: PyMuPDF                                                  │
│  Input: contract.pdf                                            │
│  Output: Raw text + page mapping                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: CLAUSE SEGMENTATION                                   │
│  Algorithm: Regex-based section splitting                       │
│  Input: Full document text                                      │
│  Output: Array of individual clauses with metadata              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: CLAUSE CLASSIFICATION                                 │
│  Current: Keyword pattern matching (41 clause types)            │
│  Future: Legal-BERT + LoRA fine-tuned on CUAD dataset           │
│  Input: Clause text                                             │
│  Output: clause_type + confidence score                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: RISK SCORING                                          │
│  Algorithm: Rule-based taxonomy mapping                         │
│  Input: clause_type                                             │
│  Output: risk_level (HIGH / MEDIUM / LOW) + overall score       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6: AI EXPLANATION (HIGH + MEDIUM clauses only)           │
│  Model: Google Gemini 2.0 Flash                                 │
│  Input: clause text + type + risk level                         │
│  Output: explanation, risks, recommendations, rewrite           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 7: CASE LAW MATCHING                                     │
│  Algorithm: Keyword + risk level similarity                     │
│  Input: clause_type + risk_level                                │
│  Output: Top 2 matching real legal cases                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 8: DASHBOARD                                             │
│  Tech: React + Recharts                                         │
│  Displays: Risk score, clause list, detail panel, case matches  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Models & Technologies Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| PDF Parsing | **PyMuPDF (fitz)** | Extract text from PDF pages |
| Segmentation | **Regex + Heuristics** | Split text into individual clauses |
| Classification (current) | **Keyword Pattern Matching** | Identify clause types from 41 categories |
| Classification (planned) | **Legal-BERT + LoRA** | ML-based classification trained on CUAD |
| Risk Mapping | **Rule-Based Taxonomy** | Map clause types → HIGH / MEDIUM / LOW |
| Explanation | **Gemini 2.0 Flash** | Generate plain-English analysis |
| Case Matching | **Similarity Scoring** | Link clauses to real legal cases |
| Calibration (planned) | **Temperature Scaling** | Calibrate model confidence scores |
| Frontend Charts | **Recharts** | Donut charts, bar charts |
| API Framework | **FastAPI** | Async Python web framework |
| Frontend Framework | **React + Vite** | UI rendering and routing |
