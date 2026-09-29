# National Weather Big Data Analytics Platform
### SIH26069 — Ministry of Earth Sciences (MoES) / India Meteorological Department (IMD)

---

## 1. Problem Statement

### 1.1 Core Problem
India's official meteorological infrastructure — radar, satellite, and ground weather stations — delivers accurate, calibrated data but at limited spatial resolution. Hyper-local and fast-onset events (flash floods, urban waterlogging, cloudbursts, hailstorms, dust storms, lightning strikes) are frequently observed and reported by citizens on social media minutes to hours *before* they register on official instruments. IMD currently has no automated, verified, real-time pipeline to capture this citizen-generated signal, filter out noise and misinformation, and fuse it with official data for faster situational awareness and warning issuance.

### 1.2 Target Audience and Pain Points
| Stakeholder | Pain Point |
|---|---|
| IMD forecasters / regional centers | No structured feed of ground-truth citizen reports to corroborate radar/satellite nowcasts |
| State Disaster Management Authorities (SDMAs) / NDRF | Delayed situational awareness for hyper-local incidents (e.g., subway flooding) not visible on regional-scale instruments |
| Citizens | No trusted, structured channel to report hazards and receive verified, hyperlocal confirmation |
| Media / researchers | No open, verified dataset of ground-truth weather-event reports tagged to time and location |

### 1.3 Problem Scope and Market Gap
Existing global tools (mPING) prove the demand for public weather reporting but lack ML-based verification, multimedia evidence, and multi-source (social + citizen + API) fusion. Existing domestic apps (Sachet, Damini, Meghdoot) are one-way alert-broadcast systems, not two-way, verified intelligence platforms. No current system combines: (a) multi-channel real-time ingestion, (b) AI-based fake/duplicate detection, (c) trust-tiered source scoring, and (d) an actionable admin dashboard for India specifically, in Indian languages, at national scale. This is the gap the platform must fill.

---

## 2. Solution Overview

### 2.1 Description
A platform that ingests weather-related signals from social media (hashtags like #IMD, #MumbaiRains), public datasets, news websites, IMD/Open-Meteo APIs, and a dedicated citizen-reporting app; runs them through an ML pipeline for classification, deduplication, and credibility scoring; routes low-confidence or high-impact reports to a human reviewer; and surfaces verified, filterable, geospatial intelligence through a public dashboard and an internal Admin Panel. The MVP runs this full workflow on a single-server, open-source stack (Section 4); higher-throughput streaming and cloud infrastructure are planned for later phases (Section 7.2).

### 2.2 How It Addresses the Problem
- Closes the "last-mile" gap between citizen observation and official confirmation by giving forecasters a live, verified, geo-tagged report stream.
- Reduces manual monitoring burden via automated categorization and fake-report filtering, instead of manual social-media watching.
- Gives SDMAs and NDRF a real-time common operating picture of hyper-local incidents.

### 2.3 Key Features and Capabilities
- Multi-source real-time ingestion across all five PS-mandated channels: social media platforms, public datasets, websites, APIs, and citizen reports (see 2.3.1)
- Standardized metadata schema captured for every record (see 2.3.2)
- ML-based event classification (rainfall, thunderstorm, flood, heatwave, fog, dust storm, strong wind)
- Three distinct, separately-scored ML verification tasks (see 2.3.3): fake/misleading report detection, untrusted-source verification, and duplicate-entry removal
- Multilingual NLP (Hindi + major regional languages, not English-only)
- Geospatial heatmap dashboard with date-wise, event-wise, location-wise, and verification-status filters
- Dedicated verification-status tracking as a first-class field (Verified / Under Review / Rejected / Unverified) visible on every record, not just a backend flag
- Admin panel for manual review, override, and escalation workflows
- Citizen reporting app/portal as the primary crowdsourced-input surface (see 6.1.1)
- Data export (GeoJSON/CSV) for NDRF and SDMAs

#### 2.3.1 Ingestion Source Breakdown
| Source (per PS) | Connector | Example |
|---|---|---|
| Social media platforms | Streaming/API connectors polling for #IMD and weather hashtags | X/Twitter, Facebook, Instagram public posts |
| Public datasets | Scheduled batch ingestion | data.gov.in, IMD open data, NASA/NOAA datasets |
| Websites | Dedicated web-crawling/scraping connector (distinct from APIs) | News portals, state disaster management department sites, district bulletins |
| APIs | Direct API integration | IMD APIs, Open-Meteo, WMO CAP alert feed |
| Citizen reports | Native mobile/web citizen app | Direct submissions with photo, video, GPS, category |

#### 2.3.2 Standard Metadata Schema
Every ingested record — regardless of source — is normalized into a common schema matching the PS requirement exactly:

| Field | Description |
|---|---|
| `timestamp` | Date & time of the observation |
| `city` | City-level location |
| `state` | State-level location |
| `gps_location` | Latitude/longitude (from device GPS or geocoded from text) |
| `photos` | Attached image(s), stored in object storage |
| `videos` | Attached video(s), stored in object storage |
| `event_category` | One of: rainfall, thunderstorm, flooding, heatwave, fog, dust storm, strong wind |
| `source_type` | social_media / public_dataset / website / api / citizen_report |
| `verification_status` | verified / under_review / rejected / unverified |
| `trust_score` | Computed source-credibility score (0–100) |

#### 2.3.3 Three Distinct ML Verification Tasks
The PS calls out three separate AI/ML responsibilities, addressed as three independent pipeline stages rather than one blended step:
1. **Fake/misleading report detection** — content-level classifier (text claims + basic image checks to flag recycled/old disaster photos).
2. **Untrusted-source verification** — source-level trust-tier scoring (official_imd, verified_partner, social_public, anonymous_citizen) based on account history, prior report accuracy, and corroboration by other reports.
3. **Duplicate-entry removal** — near-duplicate detection across text (embedding similarity) and media (perceptual hashing) to collapse repeated reports of the same event into a single verified record.

#### 2.3.4 Human-in-the-Loop Verification (Not Fully Automated)
ML output is treated as a **decision aid, not a final verdict**. Reports fall into two paths:
- **Auto-verified:** high-confidence, low-impact reports (e.g., routine rainfall confirmation) that clear ML checks are marked "Verified" automatically.
- **Human review required:** anything flagged as low-confidence, contradictory, or **high-impact** (e.g., flood, extreme event, mass-casualty potential) is routed to the Admin Panel's review queue, where a human operator makes the final call before it is marked Verified/Rejected. High-impact reports are never auto-published without human sign-off — this is a deliberate safety design choice, not a limitation of the ML.

---

## 3. Differentiation and Core Value Proposition

### 3.1 Why This Is Different from Existing Alternatives
Based on our research (publicly available information — not a formal competitive audit), mPING (NOAA/US) accepts anonymous reports without content-based verification. Ushahidi-style crisis maps are general-purpose, not tuned for weather event types. Domestic apps like Sachet and Damini are primarily one-way alert-broadcast tools rather than two-way citizen-report intake systems. Publicly visible prior attempts at this specific problem statement appear to rely on simple feed scraping with manual review, without an automated fake-detection or deduplication layer. Our approach aims to combine multilingual classification, automated fake/duplicate screening, and human-in-the-loop verification in one workflow — we present this as our design direction rather than a definitive claim about every existing or unseen solution.

### 3.2 The Major Problem Competitors Fail to Solve
Many existing tools appear to trade off speed against reliability: official channels are accurate but slow to reflect hyper-local conditions, while raw social-media feeds are fast but unverified. Our goal is a workflow that keeps a human-verification step in the loop for high-impact reports while still being fast enough to be operationally useful — we treat this as the core design goal to validate during the demo, not a guaranteed advantage over every alternative.

### 3.3 Unique Competitive Advantage and Market Positioning
We position this as a potential intake and verification layer that could sit alongside IMD's existing alerting systems (such as CAP-based alerts), feeding verified citizen/social observations into the forecasting workflow rather than replacing any existing IMD system. Any claim of technical advantage is intended to be demonstrated and validated during evaluation, not assumed.

---

## 4. Technology Stack — MVP-Focused, Open-Source First

> This is the stack we will actually build and demo. It is intentionally minimal — every item below is used directly in the MVP. Heavier, production-scale technologies (Kubernetes, Flink/Spark, Terraform, ArgoCD, multi-region replication, etc.) are **not** part of the MVP and are deferred to Section 7.2 (Future Roadmap) so the team isn't graded on infrastructure it hasn't built.

| Layer | Technology (MVP) | Why |
|---|---|---|
| Frontend | React + Tailwind CSS, MapLibre GL (open-source maps) | Fast to build, free heatmap/marker rendering |
| Backend/API | Python (FastAPI) | One language across backend + ML, simple REST API |
| Database | PostgreSQL + PostGIS | Single database for structured records + geolocation queries |
| Media storage | Local/MinIO object storage | Stores citizen photos/videos, open-source, S3-compatible |
| Real-time updates | WebSockets (Socket.IO) | Pushes new verified reports to the dashboard live, no heavy streaming engine needed at MVP scale |
| Ingestion | Python scripts/cron jobs (Tweepy/requests + BeautifulSoup) | Pulls social posts, calls APIs, scrapes news pages — sufficient for demo data volumes |
| ML/NLP | Scikit-learn/HuggingFace Transformers (a small pretrained multilingual model) | Event classification + fake/duplicate detection at MVP scale |
| Admin/Auth | FastAPI's built-in auth + JWT | Simple login-gated admin panel, no separate IAM service needed yet |

This entire stack can run on a single server/laptop for the demo — no distributed cluster required.

---

## 5. Architecture Plan

### 5.1 MVP Scope — What We Will Actually Build and Demo
To be explicit about the demo boundary:
- **Included in MVP:** citizen report submission (web form/app), one social-media connector (e.g., X/Twitter hashtag pull) + one website scraper for news, a single ML pipeline (event classification + basic fake/duplicate detection), a human review queue for flagged/high-impact reports, a live dashboard with map + filters (date, event, location, verification status), and an admin panel.
- **Not included in MVP (see 7.2 Future Roadmap):** full-scale streaming (Kafka/Flink), Kubernetes/container orchestration, multi-region database replication, CDN, advanced source-trust scoring across many platforms, and full national-scale ingestion. The MVP demonstrates the *complete workflow end-to-end* on a smaller, single-server scale, not production-grade throughput.

### 5.2 Simple End-to-End Workflow: Report → ML → Verification → Dashboard

```
[1] REPORT INTAKE
    Citizen app submission  ──┐
    Social media (#IMD posts) ─┼──►  Common intake API
    News website scrape       ──┘     (saves raw record: text, media, GPS, time)
                                         │
                                         ▼
[2] ML PROCESSING
    - Classify event type (rainfall/flood/heatwave/etc.)
    - Check for duplicates (similar text/image already seen?)
    - Score for fake/misleading content
                                         │
                                         ▼
[3] VERIFICATION
    High-confidence, low-risk  ──► Auto-marked "Verified"
    Low-confidence / high-impact ─► Sent to human Admin review queue
                                         │  (Admin approves/rejects)
                                         ▼
[4] DASHBOARD
    Verified + reviewed records shown on live map/dashboard
    Filters: date, event type, location, verification status
```

This is the one flow every component in the document maps back to — a report never reaches the public dashboard without passing through the ML check and, for high-impact cases, a human reviewer.

### 5.3 Component Overview (MVP)
| Step | Component | Technology (from Section 4) |
|---|---|---|
| Intake | Single FastAPI endpoint receiving all sources | FastAPI |
| Storage | One database for everything at MVP scale | PostgreSQL + PostGIS, MinIO for media |
| ML | Classification + fake/duplicate check runs as a background job when a new record arrives | Scikit-learn/HuggingFace |
| Human review | Admin panel queue for anything the ML flags as low-confidence or high-impact | FastAPI admin routes + simple UI |
| Live updates | Dashboard refreshes when a record is verified | Socket.IO |

### 5.4 Caching and Rate Limiting (MVP-Level)
Basic in-memory/Redis caching for frequently-viewed dashboard queries (e.g., "today's reports by state"), and simple per-IP request throttling on the citizen submission endpoint to prevent spam — both lightweight enough to run on a single server. Advanced multi-layer caching and gateway-level throttling are deferred to Section 7.2.

---

## 6. Visual Plan / UI-UX Strategy

### 6.1 Design System Approach
A single shared design-token system (colors, spacing, typography) applied consistently across the public dashboard and admin panel, with severity-color coding for event types (e.g., red for flood/extreme, amber for advisories) aligned to IMD's existing color-coded warning conventions for familiarity.

#### 6.1.1 Citizen Reporting App/Portal
Since citizen reports are one of the five PS-mandated ingestion sources, the citizen-facing surface is a first-class product, not an afterthought:
- One-screen submission flow: auto-captured GPS + timestamp, event-category picker (rainfall/thunderstorm/flood/heatwave/fog/dust storm/strong wind), optional photo/video attachment, optional free-text description.
- Available as a lightweight mobile app (Android/iOS) and a low-bandwidth web form for feature-phone/2G accessibility.
- Immediate on-screen acknowledgment plus a trackable status (Under Review → Verified/Rejected) so citizens see their report's outcome, encouraging continued participation.

### 6.2 Responsive and Adaptive Design
Mobile-first citizen reporting app; dashboard responsive from large control-room displays down to tablets used by field NDRF teams, with map/list view toggling on small screens.

### 6.3 Performance Budgets for Visual Elements
Map tile and clustering optimization to keep heatmap renders under ~2s even with thousands of concurrent markers; lazy-loading of media thumbnails; virtualized lists for report feeds.

### 6.4 User Journey Mapping for Key Flows
Key flows mapped and optimized: citizen submitting a report via the app in under 30 seconds, operator reviewing a flagged report queue and updating its verification status, forecaster filtering the map by event + date + location + verification status during an active event.

### 6.5 Verification Status as a First-Class UI Element
Every report card, map marker, and list row displays a distinct verification-status badge (Verified / Under Review / Rejected / Unverified) with consistent color coding across both the public dashboard and Admin Panel, and verification status is filterable independently of event type and location — directly matching the PS's explicit "verification status tracking" dashboard requirement.

### 6.6 Dark Mode and Theming
Dark mode by default for control-room/operations use (reduced eye strain during extended monitoring), light mode for public-facing dashboard.

### 6.7 Internationalization and Localization
UI localized in Hindi and major regional languages; NLP pipeline explicitly trained/fine-tuned for multilingual input (not translating everything to English first, which loses nuance in regional dialectal weather terms).

---

## 7. Conclusion

### 7.1 Synthesis
The platform converts an already-existing but untapped signal — citizen and social-media weather observations — into a verified, real-time, actionable intelligence layer for IMD, closing the gap left by existing broadcast-only alert systems and unverified crowdsourcing apps like mPING.

### 7.2 Future Roadmap and Evolution Path
- **Phase 1 (MVP — what we demo):** core ingestion (citizen app + one social connector + one website scraper) + ML classification/fake-detection + human review queue + live dashboard, for a handful of event types and a limited set of cities, running on a single server as described in Sections 4–5.
- **Phase 2 (Pilot scale):** introduce message-queue-based streaming (Apache Kafka) to handle higher ingestion volume, expand to full multilingual NLP coverage, mature the source trust-scoring model with real usage data, and integrate with NDRF/SDMA workflows.
- **Phase 3 (Production/national scale):** move to container orchestration (Kubernetes) for horizontal scaling, adopt Apache Flink/Spark Structured Streaming for high-throughput stream processing, introduce Infrastructure-as-Code (Terraform) and GitOps deployment (ArgoCD) for reliable multi-environment operations, add database replication/disaster-recovery setups, CDN-backed asset delivery, and predictive nowcasting fusion with radar/satellite data and IoT sensor integration (phone barometers, personal weather stations), plus a public API for researchers.

### 7.3 Risk Mitigation Summary
- Social media API access/cost changes → design connector layer to be pluggable/source-agnostic, not locked to one platform.
- Fake-report adversarial attacks → continuous model retraining, human-in-the-loop review for high-impact alerts.
- Data privacy (DPDP Act) → anonymization options, consent flows, minimal necessary data retention.
- Traffic spikes during major weather events (MVP stage) → basic per-IP rate limiting and request throttling on a single server, with a documented plan to move to message-queue-based streaming (Kafka) and horizontal scaling (Kubernetes) in Phase 2/3 if demo-stage load testing shows the single-server setup is insufficient.

### 7.4 Success Metrics and Key Performance Indicators

**Accuracy metrics**
- Event-category classification accuracy on a held-out labeled test set (target: ≥85% for MVP)
- Fake/misleading detection precision and recall against a labeled validation set (target: precision ≥80%, recall ≥75% for MVP)
- Duplicate-detection F1 score on a manually-labeled duplicate pair dataset

**Latency / speed metrics**
- End-to-end processing time: report submission → ML classification result (target: under 10 seconds per record at MVP scale)
- Time from auto-verification to dashboard appearance (target: under 30 seconds, via WebSocket push)
- Time from flagging to human-review resolution for high-impact reports (target: under 15 minutes, tracked as an operational metric, not a system-latency one)

**Error / quality metrics**
- False-positive rate: legitimate reports incorrectly flagged as fake (target: under 10% for MVP)
- False-negative rate: fake reports that pass through undetected (tracked and reported even if higher initially — transparency over a polished number)
- Human-reviewer override rate (how often operators overturn the ML's suggested verdict) — used to track ML reliability over time

**Throughput / scale metrics (for demo)**
- Number of reports the MVP pipeline can process per minute in a live demo run
- Concurrent dashboard users supported without degraded refresh performance in testing

**Adoption metrics (post-MVP)**
- Number of verified hyper-local events surfaced via citizen/social reports before confirmation by official instruments
- Dashboard usage by pilot users (e.g., a test group of forecasters or student evaluators for the demo)

All target numbers above are MVP/demo-stage goals to validate against, not guaranteed production benchmarks.
