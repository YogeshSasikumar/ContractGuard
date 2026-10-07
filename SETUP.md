# Riskora — Setup & Run Guide

## Prerequisites

- **Python** 3.10+ installed
- **Node.js** 18+ and npm installed
- **Git** installed

---

## 1. Clone the Repository

```bash
git clone https://github.com/JeevanSarasramSS/Riskora.git
cd Riskora
```

---

## 2. Backend Setup

```bash
# Navigate to backend
cd backend
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\activate
# Windows (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Create .env file in backend directory
# Windows (PowerShell):
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
# Linux / macOS:
echo 'GEMINI_API_KEY=your_gemini_api_key_here' > .env
```

> **Note:** Get a free Gemini API key from https://aistudio.google.com/apikey
> If you skip this, the system will use template-based explanations as fallback.

### Start the Backend Server

```bash
# Make sure venv is activated, then:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **First startup will be slow** (~2-5 minutes) as it downloads ML models:
> - Legal-BERT (~440MB)
> - BART-MNLI (~1.6GB)
> - Sentence-Transformers (~90MB)
>
> Subsequent starts use cached models and are much faster.

### Verify Backend is Running

```bash
# In a new terminal:
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "models": {
    "legal_bert": true,
    "bart_mnli": true,
    "sentence_transformer": true,
    "any_ml_available": true
  },
  "gemini_configured": true
}
```

---

## 3. Frontend Setup

```bash
# Open a NEW terminal, navigate to frontend
cd frontend

# Install Node.js dependencies
npm install

# Start the Vite dev server
npm run dev
```

### Verify Frontend is Running

Open your browser and go to: **http://localhost:5173**

---

## 4. Quick Reference — All Commands

### Start Everything (2 terminals needed)z

**Terminal 1 — Backend:**
```bash
cd backend
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux/macOS
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

---

## 5. Test the Pipeline

```bash
# Upload test contract via API (from backend directory)
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_contract.pdf"
```

Or use the browser UI:
1. Go to http://localhost:5173
2. Click "Start Analyzing"
3. Upload a PDF contract
4. View the risk analysis results

---

## 6. API Documentation

Once the backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Troubleshooting

### Models fail to download
```bash
# Clear Hugging Face cache and retry
pip install --upgrade transformers torch sentence-transformers
# Windows:
rmdir /s /q %USERPROFILE%\.cache\huggingface
# Linux/macOS:
rm -rf ~/.cache/huggingface
```

### Port already in use
```bash
# Kill process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
# Linux/macOS:
lsof -ti:8000 | xargs kill -9
```

### CORS errors in browser
Make sure the backend is running on port 8000 and frontend on port 5173. These are pre-configured in `app/config.py`.

### Out of memory (torch/transformers)
```bash
# Use CPU-only torch (smaller footprint)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
