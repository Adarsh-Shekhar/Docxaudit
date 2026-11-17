# Blueprint
## Plain-Language Obligation Tracker — Execution Plan

This is the master build plan. `PRD.md` says *what* to build, `TRD.md` says *how*, `rules.md` and `constraint.md` say *within what limits* — this document turns that into an ordered sequence of work with a clear "done" line at each step.

---

## 1. How These Documents Fit Together

```
PRD.md         → what the product must do, for whom, and why
TRD.md         → the architecture and zero-cost stack that implements the PRD
rules.md       → behavioral and engineering rules that apply throughout
constraint.md  → the hard limits (budget, timeline, hardware) everything fits inside
blueprint.md   → this file — the order of work, structure, and demo readiness
```

When in doubt about a build decision: check `constraint.md` first (is it even allowed within the limits?), then `rules.md` (does it violate a behavior rule?), then build it per `TRD.md`, tracking it against the phase below.

---

## 2. Repository Structure

```
obligation-tracker/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers, one file per resource (documents.py, tasks.py, ...)
│   │   ├── core/           # config, JWT/security, shared dependencies
│   │   ├── models/         # SQLAlchemy models (TRD.md Section 4)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── pipeline/       # extraction pipeline (TRD.md Section 3)
│   │   │   ├── parse.py    # PyMuPDF / python-docx ingestion
│   │   │   ├── filter.py   # spaCy + regex candidate filtering
│   │   │   ├── extract.py  # LLM call (Groq primary, Gemini/Ollama fallback)
│   │   │   └── graph.py    # LangGraph orchestration of the above
│   │   ├── services/       # business logic: tasks, notifications, evidence
│   │   └── main.py
│   ├── alembic/             # versioned migrations (rules.md: never a manual schema edit)
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # DocumentViewer, ClauseList, TaskBoard, CalendarView, ...
│   │   ├── pages/
│   │   ├── api/              # single typed API client layer (rules.md)
│   │   ├── hooks/
│   │   └── App.tsx
│   ├── tests/
│   └── package.json
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   ├── rules.md
│   ├── constraint.md
│   └── blueprint.md
├── docker-compose.yml        # local Postgres + backend for dev
└── .github/workflows/ci.yml  # lint + test on every push (free GitHub Actions minutes)
```

---

## 3. Phased Build Plan

Each phase has an explicit **Definition of Done** — don't start the next phase until the current one's line is crossed. This ordering is deliberate for a solo, time-boxed build (`constraint.md` C-2, C-3): always have a working, demoable version.

### Phase 0 — Foundations
**Implements:** infrastructure baseline, FR-5.1/FR-5.2

- [ ] Scaffold `backend/` (FastAPI) and `frontend/` (React + Vite) per the structure above *(backend through Phase 13 done: skeleton, auth, documents, full LangGraph pipeline, clauses/review API with Obligation creation — frontend React app source pending — manifest/deps installed)*
- [ ] ~~`docker-compose.yml` for local Postgres~~ → removed (2026-11-03): local dev uses a Neon dev database directly; no Docker
- [ ] GitHub repo + Actions CI (lint + test stub) *(ci.yml written; must be pushed to GitHub to verify green — pending user)*
- [x] `Organization` and `User` models + Alembic migration *(full 9-table initial migration `cc9a63fd79ed`, rollback-tested 2026-11-03)*
- [x] Register/login/JWT auth (`TRD.md` Section 2.2) *(15 backend tests pass on 2026-11-03)*
- [ ] Deploy skeleton end-to-end: frontend on Vercel, backend on Render, DB on Neon — prove the whole zero-cost pipeline works *before* building features on top of it *(= plan Phase 6, blocked on user accounts/keys; guide at `docs/deployment.md`)*

**Definition of Done:** A deployed, empty app where you can register, log in, and see a blank authenticated dashboard, entirely on free-tier infrastructure.

---

### Phase 1 — Extraction Engine
**Implements:** FR-1 (all sub-requirements)

- [ ] Document upload endpoint + storage (local disk to start)
- [ ] `parse.py`: PyMuPDF/python-docx extraction with page + character-offset preservation
- [ ] `filter.py`: spaCy + regex + `dateparser` candidate clause filtering
- [ ] `graph.py`: LangGraph pipeline wiring filter → extract → score → cite
- [ ] `extract.py`: Groq LLM call with structured-output prompt (obligation_type, plain_language_summary, key_dates, confidence)
- [ ] Async job handling + `GET /documents/{id}/status` polling endpoint
- [ ] `ExtractedClause` records persisted with full citation data

**Definition of Done:** Upload a contract via the API and, without any UI yet, confirm in the database that it produced `ExtractedClause` rows with plain-language text, obligation type, and accurate page/offset citations.

---

### Phase 2 — Verification UI
**Implements:** FR-2 (all sub-requirements) — completes the PRD's **Alpha** milestone

- [ ] PDF viewer with highlight overlay (`react-pdf` / pdf.js)
- [ ] Side-by-side extracted-clause list, synced to the highlighted span on selection
- [ ] Accept / Edit / Reject actions — Accept/Edit is the only path that writes an `Obligation` row (`rules.md` R-2)
- [ ] Per-document review progress indicator
- [ ] Low-confidence clauses visually flagged, never hidden (`rules.md` R-4)

**Definition of Done — Alpha:** Full loop works in the browser: upload → watch extraction progress → review and verify each clause → see confirmed obligations in a list. This is the first version worth demoing to anyone.

---

### Phase 3 — Task & Accountability Management
**Implements:** FR-3 (all sub-requirements)

- [ ] "Convert to task" flow from a verified Obligation
- [ ] Owner assignment from organization member list
- [ ] Evidence file upload + attachment to a task
- [ ] Task status transitions (Open → In Progress → Done) + audit log entries
- [ ] Filter/search by status, owner, due date, source document

**Definition of Done:** A verified obligation becomes a task with a named owner and due date; evidence can be attached and the task marked complete, with a visible audit trail.

---

### Phase 4 — Calendar & Alerting
**Implements:** FR-4 (all sub-requirements) — completes the PRD's **Beta** milestone

- [ ] Calendar view (`react-big-calendar`) backed by `GET /calendar`
- [ ] APScheduler job checking upcoming due dates on a schedule
- [ ] Configurable alert lead time per task/obligation type
- [ ] Email dispatch (Brevo/Resend free tier) + in-app notification center
- [ ] Snooze/dismiss without altering the underlying due date
- [ ] Recurrence handling for repeating obligations (e.g., annual renewals)

**Definition of Done — Beta:** Tasks are visible on a calendar; a test task due "tomorrow" triggers both an email and an in-app alert with the correct lead time.

---

### Phase 5 — Hardening, Accuracy Evaluation & Demo Prep
**Implements:** PRD Section 8 success metrics — completes the **Demo/Final** milestone

- [ ] Assemble a small labeled test-contract set (synthetic or public-domain — `constraint.md` C-8)
- [ ] Run the DuckDB-based precision/recall evaluation against the PRD Section 8 targets; record actual numbers
- [ ] Playwright E2E test covering the full upload → verify → task → alert flow
- [ ] Basic accessibility pass (contrast, keyboard navigation)
- [ ] Documentation pass: make sure `PRD.md`/`TRD.md`/`rules.md`/`constraint.md` reflect what was actually built, not just what was planned (`rules.md`, Part D)
- [ ] Run the Pre-Demo Checklist below

**Definition of Done:** Measured accuracy numbers exist and are documented; the full flow is rehearsed end-to-end at least once; all five project docs are current.

---

### Phase 6 — Stretch Goals (only after Phase 5 is solid)
- OCR support for scanned/image-based contracts
- Two-way Google/Outlook Calendar sync
- Migration to an Oracle Cloud "Always Free" VM if Render's cold start becomes a genuine problem
- Finer-grained recurrence rules (beyond simple yearly/monthly)

---

## 4. Pre-Demo Checklist

Free-tier infrastructure has quirks (`TRD.md` Section 7, `constraint.md` C-5) that are invisible during active development but visible the moment something's sat idle. Run through this **15–20 minutes before any demo, review, or presentation:**

- [ ] Open the Render backend URL directly once, to force it out of its idle spin-down before the audience does
- [ ] Run one query against Neon (or open the Supabase dashboard, if that's your DB) to confirm it's awake and not paused
- [ ] Check Groq's current usage against the daily cap (`console.groq.com/settings/limits`) — don't discover a 429 mid-demo
- [ ] Confirm the fallback LLM path (Gemini) still has valid credentials, in case Groq's cap is hit live
- [ ] Have one already-uploaded, already-verified sample document ready as a fallback if a live upload demo hits a slow cold start
- [ ] Confirm test email alerts are actually arriving (free email tiers occasionally land in spam — check before, not during)

---

## 5. Milestone Summary

| Milestone | Phases | What's demoable |
|---|---|---|
| **Alpha** | 0–2 | Upload, extract, verify a single document end-to-end |
| **Beta** | 3–4 | Full accountability loop: tasks, owners, evidence, calendar, alerts |
| **Demo/Final** | 5 | Measured accuracy, polished UI, rehearsed flow, current documentation |
| **Stretch** | 6 | Whatever time remains after Final is solid |

Fill in actual target dates per phase once your academic calendar is finalized — this blueprint defines the *order and definition of done*, not the calendar itself (see `constraint.md` C-2).
