# Contract Guard

**CCRAG-based Legal Contract Risk Analysis System**

AI-powered contract analysis that identifies, classifies, and explains risky clauses in legal contracts — backed by Legal-BERT, confidence calibration, and real case law.

> **Live Demo:** [riskora.vercel.app](https://riskora.vercel.app) *(lite mode — keyword classifier + Gemini API)*
> **Full ML Mode:** Run locally with Legal-BERT + BART-MNLI

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite |
| Backend | FastAPI (Python) |
| PDF Parsing | PyMuPDF (fitz) |
| AI Explanations | Google Gemini Pro API |
| ML Models | Legal-BERT + BART-MNLI (zero-shot) |
| Graph Analysis | NetworkX (clause relationship graph) |
| Case Matching | Sentence-Transformers (semantic similarity) |
| Charts | Recharts |

---

## Deployment Modes

Riskora supports two deployment modes via a single `DEPLOYMENT_MODE` environment variable:

| Mode | Models Loaded | RAM Usage | Use Case |
|------|--------------|-----------|----------|
| `full` (default) | Legal-BERT + BART-MNLI + Sentence-Transformer | ~4 GB | Local development |
| `lite` | Keyword classifier + Gemini API only | ~80 MB | Free-tier hosting (Render) |

Both modes run the **full pipeline**: PDF upload → clause extraction → classification → risk scoring → AI explanation → case law matching.

## Streamlit Deployment

The repository includes an alternative Streamlit interface in `streamlit_app.py`. It calls the existing FastAPI service, so the backend must be deployed separately (for example, on Render using `render.yaml`). The existing React/Vercel frontend remains available.

To deploy the Streamlit interface on [Streamlit Community Cloud](https://share.streamlit.io/):

1. Push this repository to GitHub and create a new Streamlit app for it, selecting `streamlit_app.py` as the app file.
2. In the app's **Settings → Secrets**, add the deployed backend URL:

   ```toml
   API_BASE_URL = "https://your-backend.onrender.com"
   ```

3. In the Render backend's environment settings, set `FRONTEND_URL` to the Streamlit app URL (for example, `https://your-app-name.streamlit.app`) so the backend allows browser requests from it.
4. Redeploy the backend after changing `FRONTEND_URL`, then restart/redeploy the Streamlit app.

The Streamlit app uses the root `requirements.txt`. Locally, install it with `pip install -r requirements.txt`, set `API_BASE_URL` if the backend is not at `http://localhost:8000`, then run `streamlit run streamlit_app.py`.

Streamlit Community Cloud hosts the Python UI, not this FastAPI backend. Keep the backend running on Render or another Python web host. Set `GEMINI_API_KEY` on the backend if you want Gemini explanations.

---

## Live Deployment (Free Tier)

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | `https://riskora.vercel.app` |
| Backend | Render | `https://riskora-backend.onrender.com` |

> **Note:** Render free tier sleeps after 15 min of inactivity. First request may take ~30-50s. Frontend always loads instantly.

---

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **Git** — [Download](https://git-scm.com/)
- *(Optional)* Google Gemini API Key — [Get one free](https://aistudio.google.com/apikey)

---



# Backend
cd backend
python -m venv venv
venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Project Structure

```
Riskora/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # App entry point
│   │   ├── config.py         # Settings & env vars
│   │   ├── routes/           # API endpoints
│   │   │   ├── upload.py     # PDF upload + analysis
│   │   │   ├── analysis.py   # On-demand classification
│   │   │   └── cases.py      # Case knowledge base
│   │   ├── services/         # Business logic
│   │   │   ├── pdf_parser.py
│   │   │   ├── clause_segmenter.py
│   │   │   ├── risk_scorer.py
│   │   │   ├── classifier.py       # Dual-model: Legal-BERT + BART-MNLI
│   │   │   ├── clause_graph.py     # NetworkX relationship graph
│   │   │   ├── gemini_explainer.py
│   │   │   └── case_matcher.py     # Semantic case matching
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic models
│   │   └── data/
│   │       ├── risk_mapping.json
│   │       └── case_knowledge_base.json
│   ├── requirements.txt       # Full dependencies (local)
│   ├── requirements-lite.txt  # Lite dependencies (deployment)
│   └── Procfile               # Render start command
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css         # Design system
│   │   ├── components/       # Reusable UI components
│   │   └── pages/            # Route pages
│   ├── package.json
│   ├── vite.config.js
│   └── vercel.json           # SPA routing for Vercel
├── render.yaml               # Render blueprint
├── streamlit_app.py          # Alternative Streamlit frontend
├── requirements.txt         # Streamlit frontend dependencies
├── .gitignore
└── README.md
```

---

## Usage

1. Open **http://localhost:5173** in your browser
2. Click **"Start Analyzing"** or navigate to `/analyze`
3. **Upload a PDF** contract (drag-and-drop or click to browse)
4. Wait for the analysis pipeline to complete:
   - Text extraction from PDF
   - Clause segmentation
   - Risk classification (41+ clause types)
   - AI explanation generation (if Gemini key is configured)
5. **Review results:**
   - Risk score overview with donut chart
   - Clause-by-clause breakdown with risk levels
   - Click any clause to see detailed explanation, risks, and suggested rewrites
   - Related real-world legal cases for each clause type
6. Browse **Case Studies** at `/cases` to explore 25 curated legal cases
7. Visit **Model Comparison** at `/comparison` to see how Riskora outperforms generic LLMs

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a PDF and run full analysis |
| `GET` | `/api/status/{job_id}` | Poll analysis progress |
| `GET` | `/api/analysis/{doc_id}` | Retrieve previous analysis |
| `GET` | `/api/analysis/{doc_id}/clauses/{clause_id}` | Get clause details |
| `POST` | `/api/analysis/explain` | Generate explanation for a clause |
| `POST` | `/api/analysis/classify` | Classify a text snippet |
| `GET` | `/api/analysis/risk-mapping` | Get the risk level mapping |
| `GET` | `/api/cases/` | List all cases (filterable) |
| `GET` | `/api/cases/{case_id}` | Get a specific case |
| `GET` | `/api/cases/match/{clause_type}` | Find matching cases |
| `GET` | `/api/health` | Health check |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEPLOYMENT_MODE` | No | `full` | `full` = all ML models, `lite` = keyword + Gemini |
| `GEMINI_API_KEY` | No | `""` | Google Gemini API key for AI explanations |
| `FRONTEND_URL` | No | `""` | Deployed frontend URL (for CORS) |
| `MODEL_PATH` | No | `./training/models/legal-bert-lora` | Path to fine-tuned model |
| `UPLOAD_DIR` | No | `./uploads` | Directory for uploaded PDFs |
| `API_BASE_URL` | Streamlit | `http://localhost:8000` | FastAPI backend base URL used by the Streamlit frontend |
