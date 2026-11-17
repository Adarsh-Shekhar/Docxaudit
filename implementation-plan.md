?# Implementation Plan — Plain-Language Obligation Tracker

> **Companion to:** `PRD.md` · `TRD.md` · `rules.md` · `constraint.md` · `blueprint.md`
> **Status:** Draft v1.0 — detailed, phase-by-phase execution plan.
> **Governing constraints:** $0 (C-1), academic timeline (C-2), solo developer (C-3), student-class hardware (C-4), free-tier ceilings (C-5), privacy/no-legal-advice (C-6), v1 scope (C-7), academic integrity (C-8).
> **Governing rules:** `rules.md` Part A (R-1…R-5), Part B (engineering), Part C (git), Part D (docs).

---

## 0. How To Use This Plan

- **Read order before starting any phase:** `constraint.md` → `rules.md` → `TRD.md` → this plan. If a phase conflicts with a constraint or rule, the constraint/rule wins and this plan must be updated (Part D of `rules.md`).
- **Phase gates:** Every phase ends with a **Definition of Done (DoD)**. Do not begin the next phase until the current phase's DoD is demonstrably met. This ordering exists specifically so there is always a working, demoable version (`constraint.md` C-2/C-3).
- **Phase numbering:** Phases are intentionally granular. A phase may be small (e.g., "add one endpoint"). Granularity makes progress measurable for a solo developer and makes it obvious when something is blocked.
- **Status tracking:** Mark each task `[x]` as complete and update `blueprint.md`'s phase/status tracking per `rules.md` Part D. Never let the docs drift.
- **Branching (`rules.md` Part C):** Each phase (or logical sub-group) gets a `feature/<short-description>` branch, PR'd into `main`. `main` is always deployable.
- **Commits (`rules.md` Part C):** Imperative mood, one logical change per commit.
- **No auto-accept (R-2):** No phase may introduce an "auto-accept high-confidence clauses" shortcut. If such a feature is ever proposed, it must be a deliberate `PRD.md` decision, not a quiet backend change.
- **Never commit:** `.env`, real contract samples, API keys, DB dumps (`rules.md` Part C).

---

## 1. Global Conventions (Apply To Every Phase)

### 1.0 Virtual Environment (mandatory)
- **All Python work runs inside a project-local `.venv`.** No global Python installs, no system-site-packages. The `.venv` directory is gitignored.
- Create it once at the repo root: `python -m venv .venv` (Windows: `python -m venv .venv`).
- Activate before any backend command:
  - Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`
  - Windows (cmd): `.\.venv\Scripts\activate.bat`
  - macOS/Linux: `source .venv/bin/activate`
- Install backend deps into it: `pip install -r backend/requirements.txt` (or `pip install -e .` if using pyproject).
- Every backend command in this plan (uvicorn, alembic, pytest, mypy, ruff, spacy download, python scripts) is assumed to run with `.venv` activated. CI recreates the venv from `requirements.txt`/`pyproject.toml`.
- Frontend has its own isolation via `node_modules` (npm/pnpm) — no global installs beyond Node itself.

### 1.1 Tech Stack (locked by TRD.md §2)
- **Frontend:** React (Vite) + Tailwind CSS + `react-pdf` (pdf.js) + `react-big-calendar` + TanStack Query.
- **Backend:** FastAPI (Python) + SQLAlchemy 2.0 + Alembic + Pydantic + python-jose (JWT) + passlib[bcrypt] + APScheduler.
- **Parsing:** PyMuPDF (fitz) for PDF, python-docx for Word.
- **Filtering:** spaCy + regex + dateparser.
- **Pipeline:** LangGraph.
- **LLM:** Groq (Llama 3.3 70B) primary; Gemini Flash free tier fallback. API-only — no local LLM installed (no Ollama).
- **DB:** PostgreSQL via Neon (free). Supabase only if bundling is preferred.
- **Storage:** local disk in dev; Cloudflare R2 if outgrown.
- **Email:** Brevo or Resend free tier.
- **Hosting:** Vercel/Cloudflare Pages (FE) + Render free web (BE).
- **Testing:** pytest + httpx (BE), Vitest + RTL (FE), Playwright (E2E), DuckDB (accuracy).

### 1.2 Engineering Rules (locked by rules.md Part B)
- Type hints on every function signature; `mypy` in CI.
- Pydantic models for all request/response schemas — no raw dicts crossing the API boundary.
- All DB access through SQLAlchemy models — never raw string-interpolated SQL.
- Every org-scoped endpoint filters by authenticated user's `organization_id` at the query level.
- Secrets in env vars only; `.env.example` documents required variables.
- FE: functional components + hooks only; single typed API client layer; loading + error states required for every async view.
- DB: every schema change via Alembic migration; FKs enforced at DB level.
- Pipeline: LLM calls behind a single provider-agnostic interface (`extract_clause(text) -> ExtractionResult`); every LLM call site has a timeout + defined failure behavior; prompts stored as versioned template files.

### 1.3 Free-Tier Ceilings To Design Around (constraint.md C-5)
- Groq: ~30 req/min, daily caps vary → candidate filtering (TRD §3 Step 3) is mandatory, never remove it.
- Render: 750 instance-hours/month, spins down after ~15 min idle → warm up before demo.
- Neon: ~0.5 GB storage, ~100 compute-hours/month → watch storage with large synthetic test sets.
- If a limit is hit: switch to documented fallback (Gemini / Oracle VM), never a paid tier.

### 1.4 Privacy & Legal Framing (R-1, R-3, C-6)
- Never present output as legal advice. Persistent, non-dismissible-by-default disclaimer on every page showing extracted/verified obligations and exported reports.
- Never phrase output as a legal conclusion ("you are not required to…") — only descriptive ("this clause appears to require…").
- Treat contract text as sensitive: no full document text in logs/error trackers; consent via use of extraction feature; all inference runs through hosted APIs (Groq/Gemini) — no local LLM.
- Never hardcode/log/commit real contract content in tests — synthetic or public-domain samples only.

### 1.5 Citation Rule (R-5)
- No `ExtractedClause` or `Obligation` may exist without page number + char offset. If a pipeline change makes this temporarily infeasible, block that clause from being surfaced rather than surfacing it without a citation.

### 1.6 Confidence Rule (R-4)
- Low confidence changes display (flag, sort to top for review), never whether it's shown. Never expose LLM's raw self-reported confidence as the sole signal — always show composite score (TRD §3 Step 5).

---

## 2. Milestone Map

| Milestone | Phases | Demoable state |
|---|---|---|
| **M0 — Foundations** | 0–6 | Skeleton deployed, auth works |
| **M1 — Alpha** | 7–18 | Upload → extract → verify end-to-end in browser |
| **M2 — Beta** | 19–29 | Full accountability loop: tasks, owners, evidence, calendar, alerts |
| **M3 — Final/Demo** | 30–36 | Measured accuracy, polished UI, rehearsed flow, current docs |
| **M4 — Stretch** | 37+ | OCR, calendar sync, VM migration, finer recurrence |

---

## 3. Phase-by-Phase Plan

### Phase 0 — Project Initialization & Local Environment
**Implements:** infrastructure baseline (blueprint §3 Phase 0)
**Milestone:** M0

**Objective:** Establish a working local development environment before any application code is written, so that every subsequent phase is buildable and testable on the developer's machine.

**Tasks:**
- [x] 0.1 Docker check: **Docker is NOT installed and will NOT be installed for now.** Decision (2026-11-03): local dev connects directly to a Neon dev database — no docker-compose needed for v1. Docker is optional/deferred (TRD §2.6 decision note); revisit only if a VM deployment (Phase 36.3 stretch) requires it.
- [x] 0.2 Confirm Python 3.11+ is installed (`python --version`) → found Python 3.14.2 (`D:\python\python.exe`).
- [x] 0.2a Create a project-local virtual environment at the repo root: `python -m venv .venv` (see Section 1.0). Do NOT use a global interpreter or conda env. → created; venv Python = 3.14.2.
- [x] 0.2b Activate `.venv` and upgrade pip: `python -m pip install --upgrade pip`. → pip 26.3 installed.
- [ ] 0.3 Confirm Node.js LTS (18+) and npm/pnpm are installed.
- [x] 0.4 (partially done) Git confirmed installed and configured (user: `Adarsh_Shekhar`, email: `adarshshekhar161@gmail.com`). **Remaining:** create the GitHub repository (private or public per institutional policy, C-8) and add it as `origin`.
- [x] 0.5 DB provider decided: **Neon** (the default). Used for both local dev (no Docker) and prod. Documented in TRD §2.6 decision note.
- [ ] 0.6 Email provider decided: **Resend** (documented in TRD §2.6). **Remaining:** create the Resend account, verify a sender address, store API key in a password manager (never in repo).
- [ ] 0.7 Create Groq account; generate an API key; note current model lineup at `console.groq.com` (TRD §2.3 caveat). Create Gemini account as fallback.
- [ ] 0.8 (Optional) Confirm Gemini fallback account/key is provisioned and reachable (used when Groq is unavailable). No local LLM installation is required — all inference is API-based.
- [x] 0.9 Create a top-level `obligation-tracker/` directory (or use current repo root) and initialize git (`git init`). → used `D:\New folder (6)` as repo root; `git init` done.

**Deliverables:** Local toolchain verified; accounts/keys provisioned and stored securely; empty git repo initialized.

**Definition of Done:** ~~`docker compose up` starts local Postgres~~ → superseded: Neon connection is verified later (Phase 6.1, and early in Phase 3 for the dev database); Python venv and Node are ready; all third-party accounts exist with keys in a password manager.

**Dependencies:** None.

**Risks/Notes:** Do not commit any keys. Create `.gitignore` in Phase 1 before any commit.

---

### Phase 1 — Repository Scaffold & CI/CD
**Implements:** blueprint §2 repository structure, §3 Phase 0 (scaffold + CI)
**Milestone:** M0

**Objective:** Create the repository layout and a minimal CI pipeline so that every subsequent change is linted and tested automatically.

**Tasks:**
- [x] 1.1 Create the directory tree per `blueprint.md` §2: → done 2026-11-03; docs kept at repo root (decision, noted in README)
  - `backend/app/{api,core,models,schemas,pipeline,services}/`
  - `backend/alembic/`, `backend/tests/`
  - `frontend/src/{components,pages,api,hooks}/`, `frontend/tests/`
  - `docs/` (copy the five existing docs here, or symlink; keep root copies if preferred — decide and document)
  - root: `.github/workflows/ci.yml`, `.env.example`, `.gitignore`, `README.md` (no `docker-compose.yml` — removed per 0.1 decision)
- [x] 1.2 Write `.gitignore` covering: `.env`, `*.pyc`, `__pycache__/`, `node_modules/`, `dist/`, `.venv/`, `*.db`, uploads/, test fixtures with real contracts. → done 2026-11-03 (`.venv/` is mandatory — never commit the virtual environment.)
- [x] 1.3 Write `.env.example` → done 2026-11-03. Constants: `DATABASE_URL`, JWT vars, `LLM_PROVIDER` + `GROQ_API_KEY`/`GROQ_MODEL`, `GEMINI_API_KEY` (optional fallback), **`RESEND_API_KEY`/`EMAIL_FROM` (Resend chosen — replaces SMTP_* per 0.6 decision)**, `STORAGE_PATH`, `FRONTEND_ORIGIN`.
- [x] 1.4 Backend `requirements.txt` → done 2026-11-03 with version ranges; uses **`psycopg[binary]` (psycopg3)** instead of psycopg2-binary (better Python 3.14 support) and adds `pydantic-settings`, `resend`, `apscheduler`. Exact pins to be frozen from the venv (1.4a).
- [ ] 1.4a All backend dependencies are installed **only** into `.venv` (never globally): `.\.venv\Scripts\pip install -r backend/requirements.txt`. Commit the lock/pin file so CI recreates the same environment.
- [x] 1.5 Frontend `package.json` → done 2026-11-03 (scripts + deps; npm resolved current versions, expected in package-lock.json after install).
- [ ] 1.6 ~~`docker-compose.yml`~~ → **Removed (2026-11-03):** no Docker in v1; local dev uses the Neon dev database directly (0.1 decision). A `.env` `DATABASE_URL` pointing at Neon is all that's needed. (If containers are ever wanted, add docker-compose as a phase 36 stretch.)
- [x] 1.7 GitHub Actions `ci.yml` → written 2026-11-03 (backend job: venv + pip + ruff + mypy + pytest; frontend job: npm ci + tsc + vitest). **Pending:** verify it runs green after the repo is pushed to GitHub (1.9).
- [x] 1.8 Write a minimal `README.md` → done 2026-11-03 (project summary, .venv setup, .env vars, docs links).
- [ ] 1.9 Initial commit + push; confirm CI runs (even if empty tests pass).

**Deliverables:** Repo tree, CI pipeline green on empty project, `.env.example`.

**Definition of Done:** `git push` triggers CI; CI completes (lint + test) green; a connectivity check against the Neon dev database succeeds (`DATABASE_URL` from `.env`).

**Dependencies:** Phase 0.

**Risks/Notes:** Keep CI fast (<5 min) so it's actually used. Pin dependency versions to avoid surprise breakage mid-term.

---

### Phase 2 — Backend Application Skeleton
**Implements:** TRD §2.2, §5; rules Part B
**Milestone:** M0

**Objective:** Stand up a minimal FastAPI app with configuration, CORS, health check, and the standard project wiring, so that feature routers can be added incrementally.

**Tasks:**
- [x] 2.1 `backend/app/core/config.py`: Pydantic `BaseSettings` loading all env vars from `.env`; fail fast on missing required vars.
- [x] 2.2 `backend/app/core/security.py`: password hashing (bcrypt via passlib), JWT encode/decode (python-jose), token expiry helpers.
- [x] 2.3 `backend/app/core/deps.py`: `get_db` (SQLAlchemy session dependency), `get_current_user` (JWT → User), `require_role(role)` guard.
- [x] 2.4 `backend/app/main.py`: FastAPI app, CORS (origins from `FRONTEND_ORIGIN`), include routers (empty for now), `/health` endpoint, lifespan handler that initializes DB connection.
- [x] 2.5 `backend/app/models/__init__.py` aggregator so Alembic can discover models.
- [x] 2.6 ~~`backend/Dockerfile`~~ → **Deferred (2026-11-03):** no Docker in v1 (0.1 decision). Render builds/starts directly from the repo (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). Add a Dockerfile only if the Oracle-VM stretch (Phase 36.3) is pursued.
- [x] 2.7 Verify local run (with `.venv` activated): `uvicorn app.main:app --reload` starts; `/health` returns 200; `/docs` (OpenAPI) renders.

**Deliverables:** Running FastAPI skeleton with health check and OpenAPI docs.

**Definition of Done:** `curl localhost:8000/health` → 200; `/docs` loads; app reads config from env without hardcoded secrets.

**Dependencies:** Phase 1.

**Risks/Notes:** Set up `mypy` + `ruff` config now (`pyproject.toml`) so CI enforces from the start.

---

### Phase 3 — Database Schema & Alembic Migrations
**Implements:** TRD §4 data model; rules Part B (DB)
**Milestone:** M0

**Objective:** Create all core SQLAlchemy models and the initial Alembic migration, enforcing the two-table separation of provisional vs. verified data (R-2) at the schema level.

**Tasks:**
- [x] 3.1 Initialize Alembic (`alembic init alembic`); configure `alembic.ini` + `env.py` to read `DATABASE_URL` from env and import models from `app.models`.
- [x] 3.2 Create models in `backend/app/models/`:
  - `organization.py`: `Organization` (id UUID PK, name, created_at).
  - `user.py`: `User` (id, organization_id FK, email unique, password_hash, role enum admin|member, created_at).
  - `document.py`: `Document` (id, organization_id FK, uploaded_by FK→User, filename, storage_path, mime_type, version int, uploaded_at).
  - `extracted_clause.py`: `ExtractedClause` (id, document_id FK, obligation_type enum, plain_language_text, raw_source_text, page_number, char_start, char_end, confidence_score float, status enum pending|accepted|edited|rejected, created_at).
  - `obligation.py`: `Obligation` (id, document_id FK, extracted_clause_id FK nullable, obligation_type, description, citation_page, citation_offset_start, citation_offset_end, created_by FK→User, verified_at).
  - `task.py`: `Task` (id, obligation_id FK, title, description, due_date, recurrence_rule nullable string, owner_id FK→User, status enum open|in_progress|done, created_at, updated_at).
  - `evidence_attachment.py`: `EvidenceAttachment` (id, task_id FK, storage_path, uploaded_by FK→User, uploaded_at).
  - `notification.py`: `Notification` (id, task_id FK, channel enum email|in_app, lead_time_days, scheduled_for, sent_at nullable, status, read_at nullable).
  - `audit_log.py`: `AuditLog` (id, organization_id FK, actor_id FK→User, entity_type, entity_id, action, timestamp, details JSONB nullable).
- [x] 3.3 Define enums as Python enums + SQLAlchemy `Enum` types (or string columns with CHECK constraints) — pick one approach and document it. → **Decision (2026-11-03):** portable enum columns via `sa.Enum(..., native_enum=False)` — string-backed with CHECK constraints. Reason: the same metadata must migrate cleanly to Neon (PostgreSQL) and run under SQLite for tests; native PG ENUM types create duplicate-type headaches in Alembic. Lowercase DB values enforced everywhere via `values_callable`.
- [x] 3.4 Add all FKs with `ondelete` policies (e.g., CASCADE for child rows where appropriate; RESTRICT where data integrity demands).
- [x] 3.5 Add indexes: unique on `User.email`; index on `Document.organization_id`, `ExtractedClause.document_id`, `Obligation.document_id`, `Task.owner_id`, `Task.due_date`, `Notification.scheduled_for`, `AuditLog.organization_id`.
- [x] 3.6 Generate initial migration (`alembic revision --autogenerate -m "initial schema"`); review the generated file by hand (autogenerate misses things — check constraints, enums).
- [ ] 3.7 Apply migration to the Neon dev database (`alembic upgrade head` with `DATABASE_URL` from `.env`); verify tables exist (Neon SQL editor or DBeaver). → **Migration itself is written and verified offline** (applied + rollback-tested on a disposable SQLite copy). **Blocked on:** user-provided Neon `DATABASE_URL`.
- [x] 3.8 Write a rollback test: `alembic downgrade -1` then `upgrade head` succeeds.

**Deliverables:** All models + initial migration; schema applied to local DB.

**Definition of Done:** `alembic upgrade head` creates all tables with FKs and indexes; `alembic downgrade base` then `upgrade head` round-trips cleanly; no raw SQL anywhere.

**Dependencies:** Phase 2.

**Risks/Notes:** The `ExtractedClause`/`Obligation` split is the enforcement mechanism for R-2 — do not merge them later. Keep `citation_page`/`citation_offset` on `Obligation` (TRD §4 design note) so verified obligations stay traceable even if extraction records are pruned.

---

### Phase 4 — Authentication & Authorization
> **Status (2026-11-03):** Implemented; 15 backend tests pass (auth, orgs, scoping, role guards, refresh typing).
**Implements:** FR-5.2, TRD §5 Auth; rules Part B
**Milestone:** M0

**Objective:** Implement standard email/password auth with JWT access + refresh tokens, plus role guards, scoped to an organization.

**Tasks:**
- [x] 4.1 `schemas/auth.py`: Pydantic `RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshRequest`.
- [x] 4.2 `api/auth.py` router:
  - `POST /auth/register`: validate input, hash password, create `Organization` + first `User` (role admin), return tokens.
  - `POST /auth/login`: verify credentials, issue access + refresh JWTs.
  - `POST /auth/refresh`: validate refresh token, issue new access token (rotate refresh token if implementing rotation).
- [x] 4.3 JWT payload: `sub` = user_id, `org` = organization_id, `role`, `exp`. Short-lived access (e.g., 15–30 min) + longer refresh (e.g., 7 days).
- [x] 4.4 `get_current_user` dependency: decode JWT, load User from DB, verify org still exists; raise 401 on invalid/expired.
- [x] 4.5 `require_role("admin")` dependency for admin-only endpoints.
- [x] 4.6 Org-scoping helper: a dependency or query filter that always injects `organization_id` from the authenticated user — never from request body/query (TRD §5).
- [x] 4.7 Tests (`tests/test_auth.py`): register, login success/failure, refresh, expired token, role guard, org scoping (user A cannot see org B's data).
- [x] 4.8 Rate-limit note: document that a brute-force limiter is a stretch goal; for v1 rely on bcrypt cost + short lockout is out of scope (acceptable per constraint C-7).

**Deliverables:** Working auth endpoints + role guards + tests.

**Definition of Done:** Full register→login→refresh flow works via `/docs`; tests pass; a request with an expired/invalid token returns 401; cross-org access returns 404/403 (never leaks existence).

**Dependencies:** Phase 3.

**Risks/Notes:** Never log tokens. Store JWT secret only in env. Use bcrypt cost factor ≥12.

---

### Phase 5 — Organization & User Management
> **Status (2026-11-03):** Implemented; audit entries on create/role-change, last-admin guard, cross-org → 404 all tested.
**Implements:** FR-5.1, TRD §5 Organizations/Users
**Milestone:** M0

**Objective:** Allow an admin to view org members, invite/add teammates, and change roles — completing the multi-user access model.

**Tasks:**
- [x] 5.1 `api/orgs.py`: `GET /orgs/me` (current org details), `POST /orgs/invite` (admin only — for v1, create user with a temp password or invite token; document the chosen approach).
- [x] 5.2 `api/users.py`: `GET /users` (list org members), `PATCH /users/{id}/role` (admin only; cannot demote the last admin).
- [x] 5.3 Invite flow decision: simplest v1 = admin creates user with email + temp password and sends credentials out-of-band (email invite link is a stretch goal). Document the decision.
- [x] 5.4 Audit log entry on role change and user creation.
- [x] 5.5 Tests: list users scoped to org; role change by admin succeeds; role change by member returns 403; cannot remove last admin.

**Deliverables:** Org/user management endpoints + tests.

**Definition of Done:** Admin can invite a member and change roles; member cannot escalate; all endpoints org-scoped and tested.

**Dependencies:** Phase 4.

**Risks/Notes:** Keep invite flow simple (C-3 solo dev). Email-based invite links can be a Phase 37 stretch item.

---

### Phase 6 — Deployment Skeleton (Zero-Cost Pipeline Proof)
> **Status (2026-11-17):** `docs/deployment.md` written (step-by-step for Neon + Render + Vercel, env var list, warm-up checklist). **All deploy tasks blocked on user accounts/keys** (GitHub repo, Neon `DATABASE_URL`, Render, Vercel). Resume with `docs/deployment.md` §1–4.
**Implements:** TRD §7; blueprint Phase 0 last item
**Milestone:** M0 (gate before feature work)

**Objective:** Prove the entire free-tier deployment pipeline works end-to-end with an empty app, so that infrastructure surprises surface now, not the night before a demo (C-2).

**Tasks:**
- [ ] 6.1 Create Neon project; obtain `DATABASE_URL`; run migrations against Neon (`alembic upgrade head`).
- [ ] 6.2 Deploy backend to Render free web service: connect GitHub repo, set env vars, build command, start command; verify `/health`.
- [ ] 6.3 Deploy frontend to Vercel/Cloudflare Pages: connect repo, set `VITE_API_BASE_URL`, build; verify blank page loads.
- [ ] 6.4 Configure CORS on backend to allow the deployed frontend origin.
- [ ] 6.5 Run the full auth flow against the deployed stack (register → login → dashboard).
- [ ] 6.6 Document cold-start behavior: note Render spin-down + Neon scale-to-zero; add to pre-demo checklist.
- [ ] 6.7 Set up GitHub Actions secrets if needed for deploy (Vercel/Render auto-deploy on push usually needs no secrets if connected via GitHub).

**Deliverables:** Deployed empty app on free-tier infra; documented cold-start caveats.

**Definition of Done:** A user can register and log in against the deployed (not local) stack, end-to-end, with no manual intervention.

**Dependencies:** Phases 1–5.

**Risks/Notes:** Do this early (C-2). Free-tier quirks (cold starts, paused DBs) must be discovered and documented now.

---

### Phase 7 — Document Ingestion & Storage (Backend)
> **Status (2026-11-17):** Done — storage abstraction (local disk, R2 stub), upload/list/get/content/delete endpoints, versioning via `replaces_document_id`, sanitized filenames, org-scoped 404s, extraction stubs (202/not_started). 10 endpoint tests pass.
**Implements:** FR-1.1, FR-1.6 (async), TRD §5 Documents
**Milestone:** M1

**Objective:** Accept PDF/DOCX uploads, store them, create `Document` rows, and reject unsupported formats with a clear error — with org scoping and access checks.

**Tasks:**
- [x] 7.1 `core/storage.py`: abstraction with two implementations — `LocalStorage` (dev) and `R2Storage` (prod, optional). Interface: `save(file, path) -> storage_path`, `read(path) -> bytes`, `delete(path)`. Default to local disk (TRD §2.4).
- [x] 7.2 `schemas/document.py`: `DocumentResponse`, `UploadResponse`.
- [x] 7.3 `api/documents.py`:
  - `POST /documents` (multipart upload): validate MIME type (PDF/DOCX only) → 415 on unsupported; size limit (e.g., 25 MB); save file; create `Document` row (version=1); return document metadata.
  - `GET /documents` (list org's documents).
  - `GET /documents/{id}` (metadata; access-checked).
  - `DELETE /documents/{id}` (admin or uploader; cascade-delete extracted clauses/obligations? Decide: block delete if verified obligations exist, or soft-delete — document the decision; default: hard delete cascades, with audit log entry).
  - `POST /documents/{id}/extract` (trigger pipeline — implemented in Phase 12; stub returns 202 here).
  - `GET /documents/{id}/status` (extraction status — implemented in Phase 12; stub returns `{status: "not_started"}`).
- [x] 7.4 Version handling for re-upload (US-8): `POST /documents` accepts optional `replaces_document_id`; if provided, increment version, mark old as superseded (add `superseded_by` nullable FK or a `status` field). For v1 simplest: create a new Document with version+1 and link via `parent_document_id` nullable. Document the approach.
- [x] 7.5 File storage path convention: `{org_id}/{document_id}/v{version}/{filename}` — never trust client filename for path; sanitize.
- [x] 7.6 Access check on every document endpoint: load Document, verify `organization_id == current_user.organization_id` else 404.
- [x] 7.7 Tests: upload PDF/DOCX succeeds; unsupported format → 415; cross-org access → 404; delete cascades; version increment on re-upload.

**Deliverables:** Document upload/list/get/delete endpoints + storage abstraction + tests.

**Definition of Done:** A PDF and a DOCX can be uploaded via `/docs` and downloaded back; unsupported format rejected with clear error; all endpoints org-scoped and tested.

**Dependencies:** Phase 5.

**Risks/Notes:** Never log document text (R-3). Sanitize filenames (path traversal). Set a max upload size to protect free-tier storage.

---

### Phase 8 — Extraction Pipeline: Parsing (`parse.py`)
> **Status (2026-11-17):** Done — offset-preserving PDF/DOCX parsing; chunks absorb trailing separators so `"".join(chunks) == full text` exactly; numbered-clause + blank-line paragraph boundaries; `NoTextLayerError` for scanned PDFs; synthetic fixture generator + 9 parse tests pass.
**Implements:** FR-1.2, TRD §3 Step 1–2
**Milestone:** M1

**Objective:** Extract raw text from PDF/DOCX with page number and character-offset metadata preserved, so every later step can cite exactly.

**Tasks:**
- [x] 8.1 `pipeline/parse.py`:
  - `parse_pdf(file_bytes) -> list[Chunk]` using PyMuPDF: iterate pages, extract text with `get_text("dict")` or `get_text()` preserving offsets; record `page_number`, `char_start`, `char_end` (global offset across the document) and `raw_text`.
  - `parse_docx(file_bytes) -> list[Chunk]` using python-docx: iterate paragraphs (and tables if present), assign page numbers as best-effort (DOCX has no native page breaks without rendering — document this limitation; use paragraph index as a fallback locator and record `page_number=None` or estimated). Record offsets.
  - `Chunk` dataclass: `text`, `page_number` (int | None), `char_start`, `char_end`, `document_id`.
- [x] 8.2 Chunking strategy: paragraph/clause-level chunks (TRD §3 Step 2). Split on blank lines / paragraph boundaries; keep each chunk's offsets contiguous and non-overlapping. Avoid splitting mid-sentence where possible.
- [x] 8.3 Handle edge cases: empty document, scanned/image PDF (no text layer) → raise a typed `NoTextLayerError` so the API can return a clear message (OCR is out of scope, C-7).
- [x] 8.4 Unit tests with synthetic PDF/DOCX fixtures (never real contracts): assert offsets reconstruct the original text when concatenated; assert page numbers correct for a multi-page PDF.
- [x] 8.5 Test fixture generation script (create a small synthetic contract PDF/DOCX with known clauses) committed under `tests/fixtures/` — synthetic only (C-8, R-3).

**Deliverables:** `parse.py` with offset-preserving parsing for PDF + DOCX + tests.

**Definition of Done:** Parsing a 10-page synthetic PDF yields chunks whose concatenated text (with offsets) exactly reproduces the extracted full text; page numbers are accurate; unit tests pass.

**Dependencies:** Phase 7.

**Risks/Notes:** PyMuPDF is AGPL (TRD §9) — fine for running as a service. Document the scanned-PDF limitation clearly in UI and docs. DOCX page numbers are inherently approximate; store `page_number` as best-effort and note in `Obligation` citation that DOCX citations use paragraph locators.

---

### Phase 9 — Extraction Pipeline: Candidate Filtering (`filter.py`)
> **Status (2026-11-17):** Done — keywords + 7 regex date/amount patterns + spaCy DATE NER; `FILTER_MIN_SIGNALS` env-tunable; zero false negatives on the obligation sentence set; text-free `FilterStats` histogram. 9 tests pass. **spaCy model `en_core_web_sm` installed in `.venv`.**
**Implements:** FR-1.3, TRD §3 Step 3
**Milestone:** M1

**Objective:** Cheap, CPU-only pre-filter that flags chunks likely to contain an obligation, so LLM calls stay under Groq's free-tier ceiling (C-5). This step is mandatory — do not remove it to "simplify."

**Tasks:**
- [x] 9.1 `pipeline/filter.py`:
  - Load spaCy model (`en_core_web_sm`) at startup; document install step (`python -m spacy download en_core_web_sm`) in README/setup.
  - Keyword/phrase matching (case-insensitive): "renew", "renewal", "terminate", "termination", "notice", "shall", "must", "obligation", "comply", "certificate", "insurance", "payment", "due", "expiration", "expire".
  - Regex patterns: date patterns (via `dateparser` + regex for explicit dates like "January 1, 2026", "30 days", "90 days' notice"), notice-period patterns ("\d+\s*days?\s*(notice|prior)"), monetary amounts, recurring terms ("annual", "quarterly", "monthly").
  - spaCy NER: extract DATE entities; flag chunks containing DATE + obligation keyword.
  - Output: each chunk annotated with `is_candidate: bool`, `matched_signals: list[str]`, `extracted_dates: list[str]` (raw strings, not yet normalized), `notice_period_days: int | None`.
- [x] 9.2 Keep all chunks (including non-candidates) available for an optional "full scan" mode, but default pipeline only sends candidates to the LLM. Non-candidates are stored as `ExtractedClause`? No — non-candidates are simply not extracted; but the UI should allow a user to trigger re-extraction with a lower threshold if they suspect a miss (R-4: never silently drop; low confidence is about display, but a non-candidate is a filtering decision — document this tension and provide a "re-scan with broader filter" escape hatch).
- [x] 9.3 Make filter thresholds configurable via env/settings (not hardcoded), so accuracy can be tuned without code changes.
- [x] 9.4 Unit tests: known obligation sentences → candidate=true; boilerplate sentences → candidate=false (or true but low signal); date extraction correctness on synthetic examples.
- [x] 9.5 Log (at INFO, no document text) the number of chunks vs. candidates per document for observability.

**Deliverables:** `filter.py` + configurable thresholds + tests.

**Definition of Done:** Filter reduces a typical 10–20 page contract's chunks to a candidate set at least 50% smaller than the full chunk set, with no false negatives on a hand-labeled synthetic test set of obligation sentences; unit tests pass.

**Dependencies:** Phase 8.

**Risks/Notes:** Tuning thresholds is an accuracy lever (PRD §8 recall target ≥85%). Track filter recall separately in Phase 31. The "re-scan with broader filter" escape hatch mitigates R-4's concern about silent dropping.

---

### Phase 10 — Extraction Pipeline: LLM Extraction (`extract.py`)
> **Status (2026-11-17):** Done (API-only) — provider-agnostic `extract_clause` behind `LLM_PROVIDER` (groq | gemini); versioned prompt `extract_clause_v1.txt`; 30s timeout, 3-retry exponential backoff on 429/5xx/timeout, typed `ExtractionFailedError`; 10 mock-provider tests pass; parse→filter→extract smoke runs end-to-end. **Live Groq/Gemini calls pending user API keys.**
**Implements:** FR-1.4, FR-1.5, TRD §3 Step 4; rules Part B (LLM interface)
**Milestone:** M1

**Objective:** Call the LLM behind a single provider-agnostic interface to produce structured extraction output (obligation type, plain-language summary, key dates, responsible party if inferable, self-reported confidence) from each candidate chunk.

**Tasks:**
- [x] 10.1 Define `ExtractionResult` Pydantic model: `obligation_type` (enum: renewal, termination_notice, payment_trigger, evidence_compliance, other), `plain_language_summary` (str), `key_dates` (list of `{date_str, normalized_date?, description}`), `responsible_party` (str | None), `llm_confidence` (float 0–1), `raw_llm_output` (str, for debugging, never logged in full per R-3).
- [x] 10.2 `pipeline/extract.py` — provider-agnostic interface:
  - `extract_clause(chunk_text: str, signals: FilterSignals) -> ExtractionResult`
  - Internally dispatches to configured provider: `groq`, `gemini`. Selected via env `LLM_PROVIDER`. (No local/Ollama provider — API-only.)
- [x] 10.3 Groq implementation (code complete; live verification pending GROQ_API_KEY): use `groq` SDK (or httpx); model from env `GROQ_MODEL` (default Llama 3.3 70B); structured output via JSON mode / function calling; timeout (e.g., 30s) with defined failure behavior.
- [x] 10.4 Gemini fallback implementation (code complete; live verification pending GEMINI_API_KEY): Google GenAI SDK; model `gemini-flash` (or current Flash).
- [x] 10.5 (Removed) No local/Ollama provider — all inference is API-based (Groq/Gemini). If a privacy-preserving local path is ever needed, it is a future, opt-in addition, not part of v1.
- [x] 10.6 Prompt template file: `backend/app/pipeline/prompts/extract_clause_v1.txt` (versioned). Prompt requests JSON matching `ExtractionResult`; instructs the model to phrase output descriptively ("this clause appears to require…"), never as legal conclusions (R-1); asks for a confidence; requires citing by quoting the source span (used for offset verification in Phase 11).
- [x] 10.7 Retry logic: on transient errors (429, 5xx, timeout), retry up to N times with exponential backoff; on persistent failure, raise typed `ExtractionFailedError` and mark document "extraction failed, retry" (TRD §6 Reliability). Never let a hung call block the queue (rules Part B).
- [x] 10.8 Rate-limit awareness: add a small delay/backoff between calls if needed; never exceed configured concurrency. Document Groq's ~30 req/min (C-5).
- [x] 10.9 Unit tests: mock the LLM provider; assert `extract_clause` returns a valid `ExtractionResult`; assert timeout/failure path marks document failed (not crash).

**Deliverables:** `extract.py` + versioned prompt template + provider implementations + tests.

**Definition of Done:** Calling `extract_clause` on a synthetic candidate chunk returns a well-formed `ExtractionResult` via Groq; switching `LLM_PROVIDER=gemini` works without code changes; failure path is graceful and tested.

**Dependencies:** Phase 9.

**Risks/Notes:** Prompts are versioned template files, not inlined strings (rules Part B). Keep `raw_llm_output` for debugging but never log full document text (R-3). Reconfirm Groq model lineup before building (TRD §2.3).

---

### Phase 11 — Extraction Pipeline: Scoring & Citation (`score`, `cite`)
**Implements:** TRD §3 Step 5–6; R-4, R-5
**Milestone:** M1

**Objective:** Compute a composite confidence (never trust LLM self-confidence alone) and verify/attach citations (page + char offsets) to every extraction; block uncitable clauses from surfacing (R-5).

**Tasks:**
- [ ] 11.1 `pipeline/score.py`:
  - Composite confidence = weighted blend of: LLM self-confidence, rule-based signal (e.g., did filter find an explicit date? +bonus; did filter match multiple keywords? +bonus), and a citation-verification signal (see 11.2).
  - Clamp to [0,1]; store as `confidence_score` on `ExtractedClause`.
  - Document the exact formula and weights in code comments + a short doc section.
- [ ] 11.2 Citation verification: the LLM is asked to quote the source span it extracted from. After extraction, fuzzy-match the quoted span back to the original chunk text (e.g., `difflib`/rapidfuzz) to confirm it exists; record the matched offset range. If no match above threshold, mark citation as unverified and lower confidence; if the chunk has only one plausible span, use it.
- [ ] 11.3 `pipeline/cite.py` (or fold into score): attach `page_number`, `char_start`, `char_end` from the source chunk to the `ExtractedClause`. If offset data is missing/invalid, raise/block — never persist a clause without citation (R-5).
- [ ] 11.4 Low-confidence handling: store the score; UI decides display (Phase 18). Pipeline never drops a candidate based on score (R-4).
- [ ] 11.5 Unit tests: composite score within [0,1]; citation verification matches a known quote; uncitable clause raises/blocked.

**Deliverables:** Scoring + citation verification + tests.

**Definition of Done:** Every `ExtractedClause` produced has a non-null `page_number`, `char_start`, `char_end`, and `confidence_score`; uncitable clauses are blocked (not persisted); tests pass.

**Dependencies:** Phase 10.

**Risks/Notes:** Fuzzy matching thresholds need tuning against the test set (Phase 31). Document the chosen threshold and rationale.

---

### Phase 12 — LangGraph Orchestration & Async Job Handling
**Implements:** FR-1.6, TRD §3 (LangGraph), §5 Documents (extract/status)
**Milestone:** M1

**Objective:** Wire parse → filter → extract → score → cite into a stateful LangGraph graph, run it asynchronously, and expose status polling — so the UI can show progress and a hung job can't block the request queue.

**Tasks:**
- [ ] 12.1 `pipeline/graph.py`: define a `TypedDict` state (`document_id`, `chunks`, `candidates`, `extractions`, `errors`, `status`). Nodes: `parse_node`, `filter_node`, `extract_node` (iterates candidates, calls LLM per candidate with timeout), `score_node`, `cite_node`, `persist_node`. Conditional edges: route low-confidence extractions to a "flag" path (visual flag in UI) — same data, different metadata; on any node exception, route to `error_node` which marks document `extraction_failed`.
- [ ] 12.2 Async execution: run the graph in a background task (FastAPI `BackgroundTasks` for v1, or a simple in-process queue). Document the limitation: in-process jobs die if the process restarts; acceptable for capstone scale. (Celery/Redis is out of scope — C-1/C-3.)
- [ ] 12.3 Status tracking: add an `extraction_status` field to `Document` (or a separate `ExtractionJob` table): `not_started | queued | parsing | filtering | extracting | scoring | completed | failed`. Update as the graph progresses. `GET /documents/{id}/status` returns `{status, progress: {done, total}, error?}`.
- [ ] 12.4 `POST /documents/{id}/extract`: enqueue job, return 202 with job status; idempotency — if already running/completed, return current status (or allow re-run which resets clauses).
- [ ] 12.5 Concurrency guard: don't run two extractions on the same document simultaneously (lock via DB status check).
- [ ] 12.6 Persist `ExtractedClause` rows only at `persist_node`, with full citation data. On failure, leave document in `failed` state with error message; don't partially persist (transactional).
- [ ] 12.7 Tests: enqueue extraction on synthetic doc → status reaches `completed`; mock LLM failure → status `failed` with message; re-run resets clauses; concurrent calls don't duplicate.

**Deliverables:** LangGraph pipeline + async jobs + status polling + tests.

**Definition of Done:** Uploading a synthetic contract and calling `/extract` results, within ~60s, in `ExtractedClause` rows with citations; status polling reflects progress; a forced LLM failure marks the document `failed` without crashing the app; all tested.

**Dependencies:** Phases 8–11.

**Risks/Notes:** In-process background tasks share the Render instance's resources; acceptable at capstone scale. Cold starts (C-5) can delay the first job — warm up before demo.

---

### Phase 13 — Clauses API & Verification Endpoints
**Implements:** FR-2.3, FR-2.4, TRD §5 Clauses
**Milestone:** M1

**Objective:** Expose extracted clauses and the accept/edit/reject actions — the only path by which an `Obligation` row may be created (R-2).

**Tasks:**
- [ ] 13.1 `schemas/clause.py`: `ClauseResponse` (includes citation, confidence, status), `ClauseUpdateRequest` (action: accept|edit|reject; edited `plain_language_text`/`obligation_type` optional).
- [ ] 13.2 `api/clauses.py`:
  - `GET /documents/{id}/clauses`: list clauses for a document (org-scoped via document access check), including citation + confidence + status.
  - `PATCH /clauses/{id}`: apply action:
    - `accept`: create `Obligation` row from clause (copy citation_page/offset), set clause status `accepted`, audit log.
    - `edit`: update clause text/type, then create `Obligation` from edited values, status `edited`, audit log.
    - `reject`: set clause status `rejected`, no `Obligation` row, audit log.
  - Idempotency: re-accepting an already-accepted clause should be a no-op or return the existing obligation (decide and document; default: 409 if already decided).
  - Role guard: only `admin` (or a "verifier" role) may accept/edit/reject; members are read-only (FR-5.1). Document the role mapping.
- [ ] 13.3 Progress helper: `GET /documents/{id}` (or clauses response) includes `{reviewed, total}` for the progress indicator (FR-2.5).
- [ ] 13.4 Tests: accept creates exactly one Obligation; edit creates Obligation with edited values; reject creates none; member cannot accept (403); re-accept returns 409; org scoping.

**Deliverables:** Clauses endpoints + role guards + tests.

**Definition of Done:** Via `/docs`, accepting a clause creates an `Obligation` row with citation; rejecting does not; member role is blocked; all tested.

**Dependencies:** Phase 12.

**Risks/Notes:** This is the R-2 enforcement point — code review must confirm no other code path creates `Obligation` rows. Add a grep/CI check if feasible.

---

### Phase 14 — Frontend Foundation & Routing
**Implements:** TRD §2.1; blueprint structure
**Milestone:** M1

**Objective:** Scaffold the React + Vite + Tailwind app with routing, a single typed API client layer, and shared layout/auth guards.

**Tasks:**
- [ ] 14.1 Initialize Vite React-TS project; configure Tailwind; set up path aliases.
- [ ] 14.2 Folder structure per blueprint: `components/`, `pages/`, `api/`, `hooks/`.
- [ ] 14.3 `api/client.ts`: single typed API client (axios or fetch wrapper) with base URL from env, JWT injection from storage, 401 → refresh/logout handling. All API calls go through here (rules Part B).
- [ ] 14.4 Routing (React Router): public routes (login, register), protected routes (dashboard, documents, tasks, calendar, notifications). Auth guard redirects unauthenticated users.
- [ ] 14.5 Shared layout: app shell with nav, org name, user menu, persistent disclaimer banner (R-1) — non-dismissible by default.
- [ ] 14.6 TanStack Query setup: `QueryClient` with sensible defaults; devtools in dev.
- [ ] 14.7 Global loading/error boundary components.
- [ ] 14.8 Type definitions mirroring backend Pydantic schemas (keep in sync; consider generating from OpenAPI later — manual for v1).
- [ ] 14.9 Lint/format: ESLint + Prettier; `tsc --noEmit` in CI.

**Deliverables:** Running FE skeleton with routing, typed API client, auth guard, disclaimer banner.

**Definition of Done:** `npm run dev` starts the app; unauthenticated users are redirected to login; the disclaimer banner is visible on every authenticated page; `tsc --noEmit` passes.

**Dependencies:** Phase 6 (deployed skeleton) is ideal but local dev suffices to start.

**Risks/Notes:** Keep the API client as the single choke point (rules Part B) so auth/token handling is centralized.

---

### Phase 15 — Authentication UI
**Implements:** FR-5.2
**Milestone:** M1

**Objective:** Login and registration pages wired to the backend auth endpoints.

**Tasks:**
- [ ] 15.1 `pages/Login.tsx`, `pages/Register.tsx`: forms with validation (email format, password min length), loading + error states (rules Part B).
- [ ] 15.2 Token storage: access token in memory (or httpOnly cookie if backend supports — v1 uses localStorage for simplicity; document the XSS trade-off and that httpOnly cookies are a hardening stretch goal). Refresh token handling.
- [ ] 15.3 On login success, store tokens, redirect to dashboard; on 401, clear and redirect to login.
- [ ] 15.4 Logout action clears tokens and query cache.
- [ ] 15.5 Tests (Vitest + RTL): form validation errors render; successful login redirects; failed login shows error message.

**Deliverables:** Login/register pages + tests.

**Definition of Done:** A new user can register and log in through the UI against the backend; loading/error states present; tests pass.

**Dependencies:** Phase 14, Phase 4.

---

### Phase 16 — Document Upload & Status UI
**Implements:** FR-1.1, FR-1.6
**Milestone:** M1

**Objective:** Let users upload PDF/DOCX, see upload progress, trigger extraction, and poll extraction status with a visible progress indicator.

**Tasks:**
- [ ] 16.1 `components/DocumentUpload.tsx`: drag-and-drop or file picker; client-side format validation (PDF/DOCX); size limit; upload progress bar.
- [ ] 16.2 `pages/Documents.tsx`: list of org documents with status badges; upload button; per-document "Extract" action.
- [ ] 16.3 Extraction trigger + polling: on "Extract", call `POST /documents/{id}/extract`, then poll `GET /documents/{id}/status` every 2s (TanStack Query `refetchInterval`) until `completed`/`failed`; show stage + progress ("Extracting clause 3 of 9").
- [ ] 16.4 Error handling: failed extraction shows error message + "Retry" button.
- [ ] 16.5 Empty states and loading states for the document list.
- [ ] 16.6 Tests: upload flow renders progress; status polling stops on completion; error state shows retry.

**Deliverables:** Document upload + extraction status UI + tests.

**Definition of Done:** Upload a PDF via the UI, trigger extraction, watch progress, and see completion — against the backend — with loading/error states throughout.

**Dependencies:** Phase 15, Phase 12.

---

### Phase 17 — PDF Viewer & Highlight Overlay
**Implements:** FR-2.1, FR-2.2, TRD §2.1
**Milestone:** M1 (Alpha-critical)

**Objective:** Render the original PDF and draw highlight boxes over extracted spans when a clause is selected — the trust-building feature (US-2).

**Tasks:**
- [ ] 17.1 `components/DocumentViewer.tsx` using `react-pdf`: render all pages (or paginated) with a worker; handle load/error states.
- [ ] 17.2 Highlight overlay: for a selected clause, compute the bounding box of `char_start..char_end` on `page_number` and render an absolutely-positioned highlight div over the PDF page. PyMuPDF provides word/char bounding boxes — store them at parse time (extend `Chunk`/`ExtractedClause` with `bbox` if needed) OR compute on the frontend via pdf.js text layer. Decision: store `bbox` (x0,y0,x1,y1 in PDF points) from PyMuPDF at parse time and pass through to the clause; simpler and more reliable. Document this.
- [ ] 17.3 Sync: selecting a clause in the list scrolls the viewer to its page and highlights; clicking a highlight selects the clause.
- [ ] 17.4 For DOCX: render as extracted text (not a PDF) with inline highlights, since pdf.js can't render DOCX. Document this limitation; optionally convert DOCX→PDF server-side (LibreOffice) is out of scope (C-7). Use a text view with highlighted spans.
- [ ] 17.5 Performance: virtualize pages if needed; keep viewer responsive during extraction polling.
- [ ] 17.6 Tests: viewer renders; highlight appears when clause selected (RTL + mocked pdf.js).

**Deliverables:** Document viewer with highlight overlay + tests.

**Definition of Done:** Selecting an extracted clause highlights the exact source span in the original PDF; clicking a highlight selects the clause; DOCX shows a highlighted text view.

**Dependencies:** Phase 16, Phase 13 (clauses with citations).

**Risks/Notes:** Storing bbox adds schema fields — add via Alembic migration (Phase 17.2 may require a migration; plan for it). pdf.js worker setup is a common pitfall — follow `react-pdf` docs exactly.

---

### Phase 18 — Verification UI (Clause List + Actions + Progress)
**Implements:** FR-2.1, FR-2.3, FR-2.4, FR-2.5; R-2, R-4
**Milestone:** M1 (Alpha DoD)

**Objective:** Complete the Alpha loop in the browser: side-by-side viewer + clause list, Accept/Edit/Reject, progress indicator, low-confidence flagging never hidden.

**Tasks:**
- [ ] 18.1 `components/ClauseList.tsx`: list clauses for a document; each shows type badge, plain-language summary, confidence indicator, status. Low-confidence clauses visually flagged (color + icon + sorted toward top for review) — never hidden (R-4).
- [ ] 18.2 `components/ClauseCard.tsx` actions: Accept, Edit (inline edit of plain-language text + type), Reject. Confirm dialogs for reject.
- [ ] 18.3 Wire actions to `PATCH /clauses/{id}`; on success, invalidate queries and update progress.
- [ ] 18.4 Progress indicator: "6 of 9 clauses reviewed" (FR-2.5) with a progress bar.
- [ ] 18.5 "Document fully reviewed" checkpoint (PRD §10 risk mitigation): when all clauses are decided, show a summary screen listing accepted obligations and a conscious "I have reviewed this document" confirmation. This makes gaps a conscious human call, not a silent one.
- [ ] 18.6 Disclaimer visible on this page (R-1) — already in layout, but ensure it's adjacent to extracted text too.
- [ ] 18.7 Tests: accept/edit/reject flows; progress updates; low-confidence clause renders flag; member role sees read-only view.

**Deliverables:** Verification UI + tests.

**Definition of Done — Alpha:** Full loop works in the browser: upload → watch extraction progress → review and verify each clause → see confirmed obligations in a list. This is the first version worth demoing.

**Dependencies:** Phase 17, Phase 13.

**Risks/Notes:** This is the Alpha milestone gate. Do not start Phase 19 until this DoD is demonstrably met (constraint C-2/C-3).

---

### Phase 19 — Obligations API & Frontend
**Implements:** TRD §5 Obligations
**Milestone:** M2

**Objective:** Surface verified obligations as a first-class list, filterable and traceable to source.

**Tasks:**
- [ ] 19.1 `api/obligations.py`: `GET /obligations` (filterable by document, type, date range), `GET /obligations/{id}` (includes citation + source document link).
- [ ] 19.2 `pages/Obligations.tsx`: list view with filters; each row links to source document + highlighted span; "Convert to task" action (Phase 21).
- [ ] 19.3 Tests: list returns only org's obligations; filters work; citation present.

**Deliverables:** Obligations endpoints + list UI + tests.

**Definition of Done:** Verified obligations appear in a filterable list with working citation links.

**Dependencies:** Phase 18.

---

### Phase 20 — Task Management Backend
**Implements:** FR-3.1, FR-3.2, FR-3.4, FR-3.5
**Milestone:** M2

**Objective:** Convert verified obligations into tasks with owner, due date, recurrence, status, and audit trail — the accountability core (G3).

**Tasks:**
- [ ] 20.1 `services/tasks.py`: business logic for task creation from an obligation, status transitions, owner assignment, filtering.
- [ ] 20.2 `api/tasks.py`:
  - `POST /tasks`: create task from obligation (or standalone) with title, description, due_date, recurrence_rule, owner_id. Validate owner is in the same org.
  - `GET /tasks`: filterable by status, owner, due_date range, source document (via obligation.document).
  - `PATCH /tasks/{id}`: update status (open→in_progress→done), owner, due_date, recurrence, title, description. Status transitions validated (e.g., done→open allowed for reopen).
  - `POST /tasks/{id}/evidence`: handled in Phase 22; stub here.
- [ ] 20.3 Audit log entry on every task mutation (FR-3.4).
- [ ] 20.4 Due date validation: must be a valid date; past dates allowed but flagged.
- [ ] 20.5 Recurrence: store simple string ("none", "yearly", "monthly", "quarterly") per TRD §4 design note. Parsing/next-date logic in Phase 29.
- [ ] 20.6 Tests: create from obligation; assign owner (same org required); status transitions; filters; audit entries written; cross-org access blocked.

**Deliverables:** Task endpoints + audit logging + tests.

**Definition of Done:** A verified obligation becomes a task with named owner and due date via API; status transitions and filters work; audit trail populated; tested.

**Dependencies:** Phase 19.

---

### Phase 21 — Task Management Frontend
**Implements:** FR-3.1, FR-3.2, FR-3.5
**Milestone:** M2

**Objective:** UI for creating, viewing, filtering, and updating tasks.

**Tasks:**
- [ ] 21.1 `pages/Tasks.tsx` / `components/TaskBoard.tsx`: list/board view of tasks with status columns or filterable table.
- [ ] 21.2 "Convert to task" flow from an Obligation: modal with title (pre-filled from obligation), due date picker, owner dropdown (org members), recurrence selector.
- [ ] 21.3 Task detail view: edit fields, status transition buttons, evidence section (Phase 22), audit trail view.
- [ ] 21.4 Filtering UI: status, owner, due-date range, source document.
- [ ] 21.5 Empty/loading/error states.
- [ ] 21.6 Tests: create task flow; status transition; filter application.

**Deliverables:** Task UI + tests.

**Definition of Done:** User can convert a verified obligation into a task with owner + due date, update status, and filter — all in the browser.

**Dependencies:** Phase 20, Phase 19.

---

### Phase 22 — Evidence Attachments
**Implements:** FR-3.3
**Milestone:** M2

**Objective:** Allow attaching one or more files to a task as proof of completion, with org-scoped access and audit logging.

**Tasks:**
- [ ] 22.1 `POST /tasks/{id}/evidence` (multipart): validate file type/size; store via storage abstraction; create `EvidenceAttachment` row; audit log.
- [ ] 22.2 `GET /tasks/{id}/evidence` list; `GET /evidence/{id}` download (access-checked via task→org).
- [ ] 22.3 `DELETE /evidence/{id}` (uploader or admin).
- [ ] 22.4 Frontend: evidence upload widget in task detail; list with download links; delete.
- [ ] 22.5 Storage path convention: `{org_id}/evidence/{task_id}/{attachment_id}/{filename}`.
- [ ] 22.6 Tests: upload/download/delete; cross-org access blocked; size/type limits enforced.

**Deliverables:** Evidence endpoints + UI + tests.

**Definition of Done:** Evidence can be attached, listed, downloaded, and deleted per task; access-scoped and tested.

**Dependencies:** Phase 21.

---

### Phase 23 — Audit Trail (Task & Clause History)
**Implements:** FR-3.4
**Milestone:** M2

**Objective:** Make the per-task audit trail visible and queryable, and ensure all mutations across the app write to `AuditLog`.

**Tasks:**
- [ ] 23.1 Audit service: `log_action(org_id, actor_id, entity_type, entity_id, action, details)` helper used by all mutating endpoints.
- [ ] 23.2 Backfill: ensure phases 13, 20, 22 (and 5) call the helper. Audit endpoints: `GET /tasks/{id}/audit` (or include in task detail response).
- [ ] 23.3 Frontend: render audit timeline in task detail ("Rahul changed status to Done on 2026-...").
- [ ] 23.4 Tests: audit entries present after mutations; scoped to org.

**Deliverables:** Centralized audit logging + UI + tests.

**Definition of Done:** Every task mutation produces an audit entry visible in the UI; tests pass.

**Dependencies:** Phase 22.

---

### Phase 24 — Calendar Backend
**Implements:** FR-4.1, TRD §5 Calendar
**Milestone:** M2

**Objective:** Provide a date-range endpoint returning tasks (and obligations) for calendar rendering.

**Tasks:**
- [ ] 24.1 `api/calendar.py`: `GET /calendar?from=&to=` returns events: each task as `{id, title, due_date, status, owner, obligation_type?}`; include obligations without tasks? Decision: include only tasks (obligations become tasks in Phase 20); document.
- [ ] 24.2 Date-range validation; max range limit (e.g., 90 days) to protect free-tier DB compute.
- [ ] 24.3 Tests: range filtering; org scoping; empty range.

**Deliverables:** Calendar endpoint + tests.

**Definition of Done:** `/calendar?from=&to=` returns correctly filtered, org-scoped events; tested.

**Dependencies:** Phase 20.

---

### Phase 25 — Calendar Frontend
**Implements:** FR-4.1
**Milestone:** M2

**Objective:** Render tasks on a month/week calendar.

**Tasks:**
- [ ] 25.1 `pages/Calendar.tsx` using `react-big-calendar`: month and week views; events from `/calendar` via TanStack Query (refetch on range change).
- [ ] 25.2 Event click → task detail; color-code by status/type.
- [ ] 25.3 "This week" / "overdue" digest view (FR-4.4): a panel listing overdue tasks and tasks due within 7 days, with quick actions.
- [ ] 25.4 Loading/error/empty states.
- [ ] 25.5 Tests: calendar renders events; view switching; digest shows overdue.

**Deliverables:** Calendar UI + digest + tests.

**Definition of Done:** Tasks visible on month/week calendar; overdue digest works; tested.

**Dependencies:** Phase 24, Phase 21.

---

### Phase 26 — Notification System Backend (Scheduling + In-App)
**Implements:** FR-4.2, FR-4.3; TRD §2.5, §5 Notifications
**Milestone:** M2

**Objective:** APScheduler job checks upcoming due dates and creates notification records with configurable lead times; in-app notification center endpoints.

**Tasks:**
- [ ] 26.1 APScheduler setup in FastAPI lifespan: a cron job (e.g., daily at 08:00 UTC) that iterates tasks, computes alert dates based on lead time, and creates `Notification` rows (channel=email + in_app) if not already scheduled (idempotent).
- [ ] 26.2 Lead time config: per task (`lead_time_days` nullable) or per obligation type (default in settings). Resolution order: task override → type default → global default.
- [ ] 26.3 `api/notifications.py`:
  - `GET /notifications` (user's org, unread first; filter read/unread).
  - `PATCH /notifications/{id}/read`.
  - `PATCH /notifications/preferences` (user's default lead times / channels).
- [ ] 26.4 Snooze/dismiss: add `snoozed_until` and `dismissed` fields (migration) — dismissing sets status `dismissed` without changing the task due date (FR-4.5).
- [ ] 26.5 Idempotency: scheduler must not create duplicate notifications for the same task+lead_time; use a unique constraint or existence check.
- [ ] 26.6 Tests: scheduler creates notifications for a task due within lead window; re-run is idempotent; read/dismiss/snooze work; org scoping.

**Deliverables:** Scheduler + notification endpoints + tests.

**Definition of Done:** A task due within the lead window produces notification rows; endpoints work; idempotent; tested.

**Dependencies:** Phase 20.

**Risks/Notes:** In-process scheduler shares the Render instance; on Render free tier the instance sleeps — scheduled jobs won't run while asleep. Document: for reliable alerting in prod, either keep instance awake (Oracle VM stretch) or accept that alerts fire on next wake. For the demo, trigger the job manually or shorten the schedule. This is a documented limitation (C-5), not a bug.

---

### Phase 27 — Email Alerts Integration
**Implements:** FR-4.3; TRD §2.5
**Milestone:** M2

**Objective:** Dispatch email alerts via Brevo/Resend free tier for due-soon/overdue tasks.

**Tasks:**
- [ ] 27.1 `services/email.py`: provider-agnostic email sender (Brevo API or SMTP or Resend API) selected via env; `send_email(to, subject, body)`; timeout + error handling; log only metadata (no contract text) (R-3).
- [ ] 27.2 Email templates: plain-text + simple HTML; include disclaimer (R-1) and a link to the task in the app (no sensitive document text in the email body beyond task title).
- [ ] 27.3 Wire into scheduler: when a notification row is created with channel=email, attempt dispatch; set `sent_at` on success; on failure, mark notification `failed` and retry next run (don't crash).
- [ ] 27.4 Opt-out: respect user notification preferences (channel toggles).
- [ ] 27.5 Tests: mock email provider; assert dispatch called with correct recipient/subject; failure path marks notification failed and doesn't crash.

**Deliverables:** Email dispatch service + templates + tests.

**Definition of Done:** A task due within the lead window triggers an email (verified in a test inbox) and an in-app notification; failure is graceful.

**Dependencies:** Phase 26.

**Risks/Notes:** Free email tiers may land in spam — verify sender domain and test before demo (pre-demo checklist). Never include full contract text in emails (R-3).

---

### Phase 28 — In-App Notification Center (Frontend)
**Implements:** FR-4.3, FR-4.5
**Milestone:** M2 (Beta DoD)

**Objective:** UI for viewing, reading, snoozing, and dismissing notifications.

**Tasks:**
- [ ] 28.1 `components/NotificationBell.tsx`: unread count badge in app shell; dropdown with recent notifications.
- [ ] 28.2 `pages/Notifications.tsx`: full list with filters (read/unread, channel); mark-as-read; dismiss; snooze (date picker).
- [ ] 28.3 Polling: refetch unread count every 30s (or on focus).
- [ ] 28.4 Tests: unread count updates; dismiss removes from default view; snooze hides until date.

**Deliverables:** Notification center UI + tests.

**Definition of Done — Beta:** Tasks visible on calendar; a test task due "tomorrow" triggers both an email and an in-app alert with the correct lead time; snooze/dismiss work without altering the due date.

**Dependencies:** Phase 27, Phase 25.

---

### Phase 29 — Recurrence Handling
**Implements:** FR-3.1 (recurrence), PRD Open Question 1
**Milestone:** M2

**Objective:** Support repeating obligations (e.g., annual insurance certificate) — auto-regenerate next year's task on completion (default assumption per PRD Open Questions; confirm before Beta).

**Tasks:**
- [ ] 29.1 Recurrence date calculator: given a task's due_date and `recurrence_rule` ("yearly"/"monthly"/"quarterly"), compute the next due date.
- [ ] 29.2 On task transition to `done` for a recurring task, auto-create the next task (same obligation, next due date, status open) — OR require manual roll-over. Decision: implement auto-regenerate as default, but make it a setting; document in PRD Open Questions resolution.
- [ ] 29.3 Surface recurrence in UI (badge, next occurrence preview).
- [ ] 29.4 Tests: completing a yearly task creates next year's task; non-recurring task does not.

**Deliverables:** Recurrence logic + UI + tests.

**Definition of Done:** Completing a recurring task creates the next occurrence automatically; tested.

**Dependencies:** Phase 28.

**Risks/Notes:** Confirm the auto-regenerate default with the user before implementing (PRD Open Question 1). If undecided, default to manual roll-over and document.

---

### Phase 30 — Hardening: Error Handling, Validation, Security Pass
**Implements:** TRD §6; rules Part B
**Milestone:** M3

**Objective:** Systematically harden the app: consistent error responses, input validation, security checks, and operational robustness.

**Tasks:**
- [ ] 30.1 Standardized error envelope: `{detail, code}` for all errors; FastAPI exception handlers for validation, not-found, forbidden, server error. Never leak stack traces or document text (R-3).
- [ ] 30.2 Input validation audit: every endpoint validates body/query/path via Pydantic; file uploads have size + type limits; date ranges bounded.
- [ ] 30.3 Security audit checklist:
  - JWT expiry + refresh rotation.
  - Org scoping present on every data endpoint (automated grep test listing all routes and asserting a dependency).
  - No raw SQL; no string interpolation.
  - Secrets only in env; `.env.example` complete; no secrets in git history (run `git log`/gitleaks if available).
  - CORS restricted to known origins.
  - File access checks on every evidence/download endpoint.
  - Password hashing cost adequate.
- [ ] 30.4 Rate limiting on auth endpoints (basic, in-memory) to slow brute force.
- [ ] 30.5 Graceful degradation: LLM provider down → document marked failed, retry available; email provider down → notification marked failed, retried next run.
- [ ] 30.6 Health check deepened: `/health` checks DB connectivity (and optionally LLM reachability without spending quota).
- [ ] 30.7 Tests: error envelope shape; validation errors return 422; security checklist items verified.

**Deliverables:** Hardened app + security checklist evidence + tests.

**Definition of Done:** Security checklist fully green; error responses consistent; no secrets in repo; tests pass.

**Dependencies:** Phase 29.

---

### Phase 31 — Accuracy Evaluation (DuckDB + Labeled Test Set)
**Implements:** PRD §8; TRD §8; constraint C-8
**Milestone:** M3

**Objective:** Measure extraction recall/precision against the PRD §8 targets and document actual numbers.

**Tasks:**
- [ ] 31.1 Assemble a labeled test-contract set: synthetic or public-domain contracts only (C-8, R-3). Target 5–10 documents, 50–100 labeled obligation clauses with ground-truth type + span.
- [ ] 31.2 Build an eval harness (Python script) that: runs the pipeline on each test doc, collects extracted clauses, compares to ground truth (match by span overlap + type), computes per-category and overall recall/precision/F1.
- [ ] 31.3 Store results in DuckDB for querying; produce a small report (markdown) with numbers vs. targets (recall ≥85%, FPR ≤20%).
- [ ] 31.4 Iterate: tune filter thresholds (Phase 9) and prompt (Phase 10) to approach targets; document each iteration's numbers.
- [ ] 31.5 Record final numbers in `PRD.md` §8 (actual, not target) and in the demo materials. Be honest — these are prototype benchmarks.
- [ ] 31.6 Tests: eval harness runs end-to-end on the test set without errors.

**Deliverables:** Labeled test set + eval harness + measured numbers + report.

**Definition of Done:** Measured accuracy numbers exist and are documented; eval harness reproducible; targets assessed (pass or documented shortfall with rationale).

**Dependencies:** Phase 30 (pipeline stable).

**Risks/Notes:** Do not use real third-party contracts without permission (C-6/C-8). Synthetic data may not reflect real-world accuracy — document this caveat.

---

### Phase 32 — End-to-End Testing (Playwright)
**Implements:** TRD §8
**Milestone:** M3

**Objective:** Script the full upload → verify → task → alert flow at least once before the demo, catching integration regressions.

**Tasks:**
- [ ] 32.1 Playwright setup in `frontend/tests/e2e/` (or root `e2e/`); configure base URL (local or deployed preview).
- [ ] 32.2 E2E scenario 1: register → login → upload synthetic PDF → wait for extraction → verify all clauses (accept/edit/reject) → confirm obligations list.
- [ ] 32.3 E2E scenario 2: convert obligation → task → assign owner → attach evidence → mark done → check audit trail.
- [ ] 32.4 E2E scenario 3: calendar shows task; notification appears; (email verified manually/out-of-band).
- [ ] 32.5 Run E2E in CI (optional, may be flaky on free runners — run locally before demos at minimum).
- [ ] 32.6 Document how to run E2E locally.

**Deliverables:** Playwright suite + docs.

**Definition of Done:** Full flow runs green locally at least once; documented.

**Dependencies:** Phase 31.

---

### Phase 33 — Accessibility Pass
**Implements:** TRD §6 (Accessibility); PRD non-goals
**Milestone:** M3

**Objective:** Basic WCAG AA hygiene: contrast, keyboard navigation, alt text.

**Tasks:**
- [ ] 33.1 Color contrast check on all text (Tailwind defaults mostly OK; verify custom colors).
- [ ] 33.2 Keyboard navigation: verification UI (clause list, accept/edit/reject, viewer scroll) fully operable without mouse; visible focus indicators.
- [ ] 33.3 Alt text on icons; ARIA labels on interactive elements; form labels associated.
- [ ] 33.4 Screen-reader sanity check on the document viewer (at minimum, announce selected clause).
- [ ] 33.5 Document findings and fixes.

**Deliverables:** Accessibility fixes + notes.

**Definition of Done:** Verification UI is keyboard-navigable; contrast passes AA; alt text present.

**Dependencies:** Phase 32.

---

### Phase 34 — Documentation Sync (rules.md Part D)
**Implements:** rules.md Part D; PRD §11
**Milestone:** M3

**Objective:** Ensure all five project docs reflect what was actually built, not just what was planned.

**Tasks:**
- [ ] 34.1 Update `PRD.md`: fill in Open Questions resolutions; record actual accuracy numbers (Phase 31); note any scope changes.
- [ ] 34.2 Update `TRD.md`: confirm stack choices match implementation; update model lineup note; document any deviations (e.g., bbox field, DOCX page-number approximation).
- [ ] 34.3 Update `constraint.md`: note any limit actually hit and how it was handled.
- [ ] 34.4 Update `rules.md`: only if a rule genuinely changed (should be rare); otherwise confirm compliance.
- [ ] 34.5 Update `blueprint.md`: mark phases complete; update status tracking; record actual dates.
- [ ] 34.6 Update this implementation plan: mark completed phases; note deviations.
- [ ] 34.7 Update `README.md`: final run instructions, env vars, demo steps.

**Deliverables:** All docs current.

**Definition of Done:** A reader can understand the built system from the docs alone; no drift between docs and code.

**Dependencies:** Phase 33.

---

### Phase 35 — Pre-Demo Checklist & Rehearsal
**Implements:** blueprint §4; TRD §7
**Milestone:** M3 (Demo/Final DoD)

**Objective:** Run the pre-demo checklist and rehearse the full flow end-to-end at least once.

**Tasks:**
- [ ] 35.1 Run the full Pre-Demo Checklist (blueprint §4):
  - [ ] Open Render backend URL to wake it.
  - [ ] Run a query against Neon to wake it.
  - [ ] Check Groq usage vs. daily cap.
  - [ ] Confirm Gemini fallback credentials valid.
  - [ ] Have a pre-uploaded, pre-verified sample document ready as fallback.
  - [ ] Confirm test emails actually arrive (check spam).
- [ ] 35.2 Rehearse the demo script end-to-end (upload → extract → verify → task → calendar → alert) with timing.
- [ ] 35.3 Prepare a fallback plan for each likely failure (cold start, 429, email in spam).
- [ ] 35.4 Final deploy of `main` to Vercel + Render; smoke-test deployed stack.
- [ ] 35.5 Tag a release (`v1.0-demo`) in git.

**Deliverables:** Rehearsed demo + tagged release.

**Definition of Done — Demo/Final:** Measured accuracy numbers exist and are documented; the full flow is rehearsed end-to-end at least once; all five project docs are current; deployed stack smoke-tested.

**Dependencies:** Phase 34.

---

### Phase 36 — Stretch Goals (only after Phase 35 is solid)
**Implements:** PRD Non-Goals revisits; blueprint Phase 6
**Milestone:** M4

**Objective:** Only after the Final milestone is solid, attempt stretch items. Each is independently scoped; none may destabilize `main`.

**Tasks (each optional, separate branch + PR):**
- [ ] 36.1 OCR for scanned/image-based contracts (separate project in its own right — C-7; only if time permits).
- [ ] 36.2 Two-way Google/Outlook Calendar sync (OAuth integration — significant scope; only if time permits).
- [ ] 36.3 Migration to Oracle Cloud "Always Free" VM if Render cold start becomes a genuine problem (verify account offering first — TRD §2.6).
- [ ] 36.4 Finer-grained recurrence rules (beyond simple yearly/monthly/quarterly).
- [ ] 36.5 httpOnly-cookie auth hardening (move tokens out of localStorage).
- [ ] 36.6 Email-based invite links for org members.
- [ ] 36.7 Brute-force rate limiter on auth (if not done in Phase 30).
- [ ] 36.8 Re-scan with broader filter escape hatch (if not done in Phase 9).

**Deliverables:** Whatever completes, on separate branches.

**Definition of Done:** Each stretch item independently merged to `main` only if it doesn't regress the E2E suite.

**Dependencies:** Phase 35 complete and stable.

---

## 4. Cross-Cutting Concerns (Apply Across All Phases)

### 4.1 Privacy (R-3)
- No full document text in logs, error trackers, or LLM provider logs beyond provider retention.
- Consent via use of extraction feature; state plainly in onboarding/help text.
- All inference uses hosted APIs (Groq/Gemini); review provider data-retention policies and obtain user consent via the extraction feature (no local LLM).
- Never commit real contract content; synthetic/public-domain samples only.

### 4.2 Legal Framing (R-1)
- Persistent, non-dismissible-by-default disclaimer on every page showing extracted/verified obligations and exported reports.
- Language: descriptive ("this clause appears to require…"), never conclusive ("you are not required to…").

### 4.3 Citation (R-5)
- No `ExtractedClause`/`Obligation` without page + offset. Block uncitable clauses from surfacing.

### 4.4 Confidence (R-4)
- Low confidence changes display, never visibility. Always show composite score.

### 4.5 No Auto-Accept (R-2)
- `Obligation` rows only via human Accept/Edit. No batch auto-accept, even opt-in.

### 4.6 Testing Discipline (TRD §8)
- BE: pytest + httpx; mock LLM in unit tests.
- FE: Vitest + RTL.
- E2E: Playwright.
- Accuracy: DuckDB + labeled set.

### 4.7 Git/Workflow (rules Part C)
- Branch per phase/feature; PR into `main`; `main` always deployable.
- Imperative commits; one logical change per commit.
- Never commit `.env`, real contracts, keys, DB dumps.

### 4.8 Docs (rules Part D)
- Update docs in the same change when a decision changes them.
- Update `blueprint.md` status tracking as phases complete.

---

## 5. Risk Register (Project-Level)

| Risk | Impact | Mitigation | Phase |
|---|---|---|---|
| Users over-trust AI, skip verification | Missed obligation (core failure mode) | Mandatory verification (R-2); "document fully reviewed" checkpoint | 18 |
| Extraction misses an obligation (false negative) | Silent gap | Track recall (§8); "re-scan broader filter" escape hatch; never silently drop | 9, 31 |
| Users mistake summaries for legal advice | Reputational/legal exposure | Persistent disclaimer (R-1); descriptive language only | 1, 14, 18 |
| Free-tier limits hit during demo | Downtime at worst moment | Pre-demo checklist; fallback LLM; warm-up | 6, 35 |
| Render/Neon cold start | Latency on first request | Warm-up before demo; document as known limit | 6, 35 |
| Groq model retired/changed | Pipeline breakage | Reconfirm lineup before building; provider-agnostic interface | 10 |
| Solo timeline slip | Incomplete feature set | Strict phase ordering; smaller working set over larger broken one (C-2/C-3) | all |
| DOCX page numbers approximate | Citation imprecision on DOCX | Document limitation; paragraph-locator fallback | 8, 17 |
| Scanned PDFs (no text layer) | Cannot extract | Clear error; OCR is out of scope (C-7) | 8 |
| In-process scheduler sleeps on Render | Alerts delayed | Document limitation; manual trigger for demo; VM stretch goal | 26, 36 |

---

## 6. Open Questions (Carried From PRD §12 — Resolve Before/During Build)

1. **Recurring obligations:** auto-regenerate next task on completion, or manual roll-over? Default assumption: auto-regenerate. **Resolve before Phase 29.**
2. **OCR for scanned contracts:** out of scope for v1 (C-7). Confirm no change.
3. **Pilot/test org:** synthetic test-contract set vs. real org. Decision affects Phase 31 data. **Resolve before Phase 31.**
4. **Invite flow:** admin creates user with temp password (simple) vs. email invite link (stretch). Default: simple. **Resolve before Phase 5.**
5. **Token storage:** localStorage (simple) vs. httpOnly cookie (harder). Default: localStorage; hardening is Phase 36.5. **Resolve before Phase 15.**
6. **DOCX citation precision:** best-effort page numbers acceptable? Default: yes, document. **Resolve before Phase 8.**

---

## 7. Phase Dependency Summary (Critical Path)

```
0 → 1 → 2 → 3 → 4 → 5 → 6  (foundations + deploy proof)
6 → 7 → 8 → 9 → 10 → 11 → 12 → 13  (extraction engine + verification API)
13 → 14 → 15 → 16 → 17 → 18  (Alpha UI)  ← M1 gate
18 → 19 → 20 → 21 → 22 → 23  (tasks + evidence + audit)
23 → 24 → 25  (calendar)
20 → 26 → 27 → 28  (notifications + email + center)  ← M2 gate
28 → 29  (recurrence)
29 → 30 → 31 → 32 → 33 → 34 → 35  (hardening + accuracy + E2E + a11y + docs + demo)  ← M3 gate
35 → 36  (stretch)
```

No phase may begin until its predecessors' DoD is met. If a predecessor is blocked, stop and resolve the blocker rather than starting downstream work (C-3).

---

## 8. Definition of Done — Global (applies to every phase)

A phase is "done" only when ALL of the following hold:
1. All tasks in the phase are checked `[x]`.
2. The phase's stated **Definition of Done** is demonstrably met (show, don't assert).
3. Tests for the phase pass in CI.
4. No new lint/type errors introduced.
5. `blueprint.md` status tracking updated for the phase.
6. If the phase changed anything recorded in `PRD.md`/`TRD.md`/`constraint.md`/`rules.md`, those docs are updated in the same change (Part D).

---

## 9. Next Action

This plan is ready to execute. Begin with **Phase 0** (environment verification) against `D:\New folder (6)`. No code should be written until Phase 0 is complete and verified.