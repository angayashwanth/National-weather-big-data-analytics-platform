# Standing Rules for AI Agents (National Weather Big Data Analytics Platform - SIH26069)

This document contains standing rules and operating constraints for all AI agents and developers working in this repository. The source of truth for architecture and problem statement is [docs/SIH26069_Solution_Document.md](docs/SIH26069_Solution_Document.md).

---

## 1. Approved Technology Stack

- **Backend:** Python (FastAPI)
- **Frontend:** React + Vite + Tailwind CSS + MapLibre GL
- **Database:** PostgreSQL with PostGIS in staging/production; **SQLite fallback** via `DATABASE_URL` configuration for seamless local development without external service dependencies.
- **Media Storage:** MinIO / local object storage abstraction for citizen photos/videos.
- **Real-Time Updates:** WebSockets (Socket.IO or FastAPI native WebSockets) for streaming verified reports to dashboards.
- **ML / NLP:** Scikit-learn / HuggingFace Transformers (small, fast models suitable for local inference).
- **Authentication:** FastAPI built-in JWT authentication for the Admin Panel.

---

## 2. Strict Scope Boundary — MVP Only (Section 5.1)

Build **only** the MVP scope defined in Section 5.1 of [docs/SIH26069_Solution_Document.md](docs/SIH26069_Solution_Document.md):

### Included in MVP:
1. **Citizen report intake:** Web form / submission endpoint capturing timestamp, city, state, GPS, event category, description, and optional photo/video.
2. **External ingestion connectors:**
   - One social media connector (e.g. X/Twitter hashtag ingestion or simulated feed polling for `#IMD`, `#MumbaiRains`, etc.).
   - One news website scraper connector.
3. **ML Pipeline (3 distinct responsibilities):**
   - Event classification (rainfall, thunderstorm, flooding, heatwave, fog, dust storm, strong wind).
   - Basic fake/misleading report detection.
   - Duplicate-entry detection (near-duplicate text/content).
4. **Human Review Queue:** Admin review queue for low-confidence or high-impact reports (e.g., floods/extremes). High-impact reports are never auto-published.
5. **Interactive Dashboard:** Live map with MapLibre GL, filters (date, event type, location, verification status), and real-time updates.
6. **Admin Panel:** Review queue, report approvals/rejections, and audit trails.

### Strictly Prohibited (Do NOT Add):
- **NO Apache Kafka**
- **NO Kubernetes or container orchestration**
- **NO Apache Flink / Spark**
- **NO Terraform / Cloud Infrastructure-as-Code**
- **NO complex microservice architectures**

Everything must run on a single local machine / server.

---

## 3. Environment & Execution Constraints

- **Operating System:** Windows 11.
- **Shell:** PowerShell.
- **Python Virtual Environment:** Use the virtual environment located at `.venv` (`.\.venv\Scripts\Activate.ps1` or `.\.venv\Scripts\python.exe`).
- **Command Compatibility:** All proposed shell commands **must** be valid in PowerShell. Never propose bash-specific commands (such as `export FOO=bar`, `source .venv/bin/activate`, `&&` chained bash syntax when incompatible, or Linux path separators in shell invocations).
- **Paths:** Be mindful of Windows paths, quoting, and PowerShell execution policies.

---

## 4. Testing & Verification Mandate

- **Automated Tests for Every Feature:** Every new endpoint, ingestion connector, ML stage, and frontend component/service must have automated tests.
- **Never claim something works without running it:** You must execute the test suite (e.g., `pytest` for backend, `npm test` or component tests for frontend) and verify it passes with zero failures.
- **Show command output:** In every walkthrough or report, always present the exact PowerShell command executed and the verbatim test output showing success.
- **Self-contained tests:** Tests should run offline without depending on live external APIs (use mocking/fixtures for social media, scraping, and external APIs).

---

## 5. Code Style & Simplicity

- **Keep files small and simple:** Avoid bloated monolithic files. Break logic into concise, readable modules.
- **No unnecessary abstractions:** Do not build speculative abstractions, complex inheritance hierarchies, or premature plugin engines. Write direct, explicit, and readable code.
- **Documented contracts:** Use standard Pydantic models for request/response schemas matching the PS specification.

---

## 6. Standard Metadata Schema (Section 2.3.2)

Every ingested record across all sources must normalize to this core schema:

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO-8601 DateTime | Observation date and time |
| `city` | String | City-level location |
| `state` | String | State-level location |
| `gps_location` | Object / GeoJSON | `{ "latitude": float, "longitude": float }` |
| `photos` | List[String] | Storage URLs / file paths for media |
| `videos` | List[String] | Storage URLs / file paths for media |
| `event_category` | Enum | `rainfall`, `thunderstorm`, `flooding`, `heatwave`, `fog`, `dust_storm`, `strong_wind` |
| `source_type` | Enum | `citizen_report`, `social_media`, `website`, `api`, `public_dataset` |
| `verification_status` | Enum | `verified`, `under_review`, `rejected`, `unverified` |
| `trust_score` | Float | Calculated credibility score (0–100) |

---

## 7. Repository Layout

```
National-weather-big-data-analytics-platform/
├── AGENTS.md                  # This file - standing agent instructions
├── README.md                  # Project overview and run instructions
├── .gitignore                 # Ignored files for Python, Node, media, envs
├── docs/                      # Documentation and solution specifications
│   └── SIH26069_Solution_Document.md
├── backend/                   # FastAPI application, database models, ML pipeline, tests
├── frontend/                  # React + Vite + Tailwind + MapLibre GL application
└── scripts/                   # Ingestion scripts, seeding utilities, and helpers
```
