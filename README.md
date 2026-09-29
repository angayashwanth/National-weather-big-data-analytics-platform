# National Weather Big Data Analytics Platform (SIH26069)

### Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)

A real-time intelligence platform that ingests crowdsourced citizen reports, social media posts, news websites, and meteorological feeds; verifies them through ML classification, fake detection, and duplicate checks; routes sensitive/high-impact alerts to a human review queue; and surfaces verified weather intelligence on an interactive geospatial dashboard.

The architectural source of truth for this project is [docs/SIH26069_Solution_Document.md](docs/SIH26069_Solution_Document.md). Standing rules and development constraints for AI agents and contributors are in [AGENTS.md](AGENTS.md).

---

## Technology Stack

- **Backend:** Python FastAPI, Pydantic, SQLAlchemy
- **Frontend:** React, Vite, Tailwind CSS, MapLibre GL
- **Database:** PostgreSQL + PostGIS (Production) with automatic **SQLite fallback** via `DATABASE_URL` for lightweight local development
- **Media Storage:** MinIO / local object storage for citizen photo/video uploads
- **ML / NLP:** Scikit-learn, HuggingFace Transformers (event classification, duplicate detection, fake report scoring)
- **Real-Time Streaming:** WebSockets for live dashboard updates
- **Environment:** Windows 11 + PowerShell

---

## Directory Structure

```
National-weather-big-data-analytics-platform/
├── AGENTS.md                            # Standing rules and constraints for AI agents
├── README.md                            # Project overview and setup instructions
├── .gitignore                           # Git ignore rules for Python, Node, Vite, SQLite
├── docs/
│   └── SIH26069_Solution_Document.md    # Source of truth specification document
├── backend/                             # FastAPI application, database models, ML pipeline, tests
├── frontend/                            # React + Vite + Tailwind + MapLibre GL UI
└── scripts/                             # Ingestion jobs, seeding scripts, and helper utilities
```

---

## Prerequisites (Windows 11)

Ensure the following tools are installed on your Windows machine:
1. **Python 3.11+** (Verify with `python --version`)
2. **Node.js 18+ & npm** (Verify with `node --version` and `npm --version`)
3. **PowerShell** (Default terminal on Windows 11)

---

## Getting Started & Run Instructions

All commands below are designed to be run in **PowerShell**.

### 1. Backend Setup

Open a PowerShell terminal at the repository root:

```powershell
# 1. Create a virtual environment at .venv (if not already created)
python -m venv .venv

# 2. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install backend dependencies
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

# 4. Database configuration (Optional)
# By default, SQLite (sqlite+aiosqlite:///./wx.db) is used out of the box with zero configuration.
# Database tables are created automatically when the FastAPI server starts up.
# If connecting to PostgreSQL in production/staging, you can set:
# $env:DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/weather_platform"

# 5. Start the FastAPI development server with auto-reload
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend API and Swagger docs will be accessible at:
- **API Root:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Admin Credentials (Default):**
  - Username: `admin`
  - Password: `changeme`

#### (Optional) Seed Demo Incident Data
While the FastAPI server is running on `127.0.0.1:8000`, open another PowerShell terminal (with `.venv` activated) to populate realistic Mumbai flash-flood demo reports:
```powershell
python scripts/seed.py
```

---

### 2. Frontend Setup

In a separate PowerShell terminal:

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

The frontend application will be accessible at:
- **Web Application:** `http://localhost:5173`

---

### 3. Running Automated Tests

Per project rules, every feature must have automated tests that pass before claiming completion.

#### Run Backend Tests:
```powershell
# In PowerShell with .venv activated:
pytest backend/tests/ -v
```

#### Run Frontend Tests:
```powershell
cd frontend
npm test
```

---

## Workflow Overview

1. **Intake:** Citizen reports and connector inputs (social media `#IMD`, news scraper) arrive at the unified intake API.
2. **ML Processing:** Pipeline classifies the event category, checks for duplicates, and assigns a fake/credibility score.
3. **Verification Decision:**
   - Low-risk, high-confidence reports are auto-verified.
   - High-impact hazards (floods, extreme events) or low-confidence reports are queued for Admin human review.
4. **Dashboard:** Verified records are broadcast via WebSockets to the MapLibre GL dashboard with interactive filters (date, event type, location, verification status).
