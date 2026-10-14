# DeepGuard — AI-Powered Deepfake Identification Platform

> **Important:** DeepGuard provides **probabilistic forensic analysis**, not definitive proof.  
> Results are indicators based on three forensic stages. No tool can guarantee whether an image is real or AI-generated.

---

## Architecture Overview

```
deepguard/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # Route handlers (auth, analysis, api_keys, usage, health, users)
│   │   ├── ml/               # Model loader, preprocessing, ensemble
│   │   ├── models/           # MongoDB document schemas
│   │   ├── services/         # Business logic (auth, OTP, API keys, analysis, storage)
│   │   ├── utils/            # Security (bcrypt/JWT/OTP), validators, logging
│   │   ├── config.py         # Pydantic settings (all from env)
│   │   ├── database.py       # Async Motor MongoDB connection
│   │   └── main.py           # FastAPI app factory + lifespan
│   ├── tests/                # pytest test suite
│   ├── .env                  # Local environment config
│   └── requirements.txt
│
├── frontend/                 # React + Vite + TypeScript
│   ├── src/
│   │   ├── contexts/         # AuthContext, ToastContext
│   │   ├── layouts/          # DashboardLayout
│   │   ├── pages/            # All 9 pages
│   │   ├── services/         # API service layer
│   │   └── types/            # TypeScript types
│   └── .env
│
└── ../model_train/           # EXISTING trained .h5 models (preserved, untouched)
    ├── color_pattern_model.h5
    ├── facial_pattern_model.h5
    ├── texture_pattern_model.h5
    ├── temporal_feature_model.h5
    └── eye_blink_model.h5 (or artifact_pattern_model.h5)
```

## Three-Stage Forensic Pipeline

| Stage | Weight | What it checks |
|-------|--------|----------------|
| 1 — Provenance | 30% | Metadata/PNG text chunks for AI generator signatures (Stable Diffusion, DALL-E, Midjourney, etc.) |
| 2 — Metadata | 10% | EXIF consistency, camera fingerprints, editing software traces |
| 3 — ML Ensemble | 60% | 5 trained binary classifiers (color, facial, texture, temporal, artifact patterns) |

Evidence is fused via weighted voting → final assessment + confidence score.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB running locally on port 27017
- TensorFlow (`pip install tensorflow` or `tensorflow-cpu`)

### 1. Backend

```powershell
cd "original main\deepguard\backend"

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy env (already created at .env — review MODEL_DIRECTORY path)
# Default: MODEL_DIRECTORY points to ../../model_train (your existing models)

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be at: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

### 2. Frontend

```powershell
cd "original main\deepguard\frontend"
npm install
npm run dev
```

Frontend at: http://localhost:5173

## API Authentication

Two authentication methods:

| Method | Format | Use case |
|--------|--------|----------|
| JWT | `Authorization: Bearer <jwt_token>` | Web dashboard |
| API Key | `Authorization: Bearer dg_live_<key>` | Developer integration |

## Key Features

- **Secure signup** with email OTP verification (dev mode prints to console)
- **JWT sessions** (24h) + **API key management** (create / revoke / delete)
- **Three-stage pipeline** with evidence fusion and confidence scoring
- **Privacy controls** — choose image retention per API key (immediate delete / 7d / 30d / 90d)
- **Model improvement opt-in** — explicit consent only, never silent
- **Usage tracking** — per-API-key request counters, monthly limits, history
- **Background cleanup** — expired images deleted on schedule

## Running Tests

```powershell
cd "original main\deepguard\backend"
pytest tests/ -v
```

Tests cover: password hashing, JWT, API key generation, OTP, image validator, provenance detector, metadata analyzer, ML ensemble, evidence fusion.

## Data Retention & Privacy

- **No image is retained by default** for web UI users (immediate deletion)
- API key customers choose their own retention policy at key creation
- Privacy consent records are stored separately for audit purposes
- Model training opt-in requires **explicit checkbox** — never automatic

## Model Information

The five `.h5` models in `model_train/` are binary classifiers:
- Input: 224×224 RGB images, normalized ÷ 255
- Output: Sigmoid score → `> 0.5` leans **Real**, `≤ 0.5` leans **Fake**
- Architecture: CNN backbone → Flatten → Dense(128) → Dense(64) → Sigmoid
- These are **pattern analyzers, not specialized domain algorithms**

> **Disclaimer:** Model scores are raw sigmoid outputs — not calibrated probabilities. The ensemble result is one of multiple forensic signals used in the final assessment.
