# Rules
## Plain-Language Obligation Tracker

This file is the operating rulebook for the project — for you, for any collaborator, and for any AI coding assistant (Claude Code, Copilot, etc.) working in this repository. `PRD.md` and `TRD.md` reference several of these rules directly by ID; treat this file as binding, not as a suggestion list.

---

## Part A — Product & AI Behavior Rules

These rules govern how the *application itself* is allowed to behave. They exist because this is a legal-adjacent product, and the cost of getting these wrong is a user trusting something they shouldn't.

### R-1 — Never present output as legal advice
- Every plain-language summary, every page in the UI that shows extracted or verified obligations, and any exported report must carry a visible, non-dismissible-by-default disclaimer that this is an AI-assisted reading aid, not legal advice.
- The system must never phrase output as a legal conclusion ("you are not required to...") — only as a description of what the document appears to say ("this clause appears to require...").
- Do not remove or visually bury this disclaimer to make the UI "cleaner." It is a product requirement, not a legal-team afterthought.

### R-2 — Nothing is real until a human accepts it
- An `ExtractedClause` is provisional by construction. It must never be surfaced, counted, or alerted on as if it were a confirmed `Obligation`.
- Only a human action (Accept/Edit in the Verification UI) may create a row in the `Obligation` table. No batch "auto-accept high-confidence clauses" shortcut, even as an opt-in power-user feature — this directly contradicts the product's core trust model (see `PRD.md`, Section 10, first risk).
- If this rule is ever revisited, it must be a deliberate product decision made in `PRD.md`, not a quiet backend change.

### R-3 — Treat contract text as sensitive by default
- Documents uploaded to this system are real legal agreements, potentially containing commercially sensitive terms. Do not log full document text to application logs, error trackers, or LLM provider request logs beyond what the provider itself retains.
- Before sending document text to a third-party LLM API (Groq, Gemini), make sure the user has implicitly consented by using the extraction feature — this is expected given the product's purpose, but should be stated plainly in any onboarding/help text, not hidden in fine print.
- If a document is marked (or clearly appears to be) highly sensitive, the local Ollama path (`TRD.md`, Section 2.3) is the privacy-preserving option — keep it working, don't let it silently bit-rot in favor of only the hosted path.
- Never hardcode, log, or commit real contract content used for testing. Use synthetic or already-public sample contracts for test fixtures.

### R-4 — Confidence scores inform the UI, they don't gate correctness
- A low confidence score should change how something is *displayed* (a visible flag, sorted toward the top for review) — never whether it's *shown at all*. Silently dropping low-confidence candidates reintroduces the missed-obligation failure mode this product exists to prevent.
- Never expose the LLM's raw self-reported confidence number as the sole confidence signal to the user; always show the composite score described in `TRD.md`, Section 3, Step 5.

### R-5 — Citations are mandatory, not optional metadata
- No `ExtractedClause` or `Obligation` may exist without a page number and character offset back to the source document. If a pipeline change makes this temporarily infeasible, block that clause from being surfaced rather than surfacing it without a citation.

---

## Part B — Engineering Conventions

### Backend (FastAPI / Python)
- Type hints on every function signature; run `mypy` (or equivalent) in CI.
- Pydantic models for all request/response schemas — no raw dicts crossing the API boundary.
- All database access through SQLAlchemy models, never raw string-interpolated SQL (prevents SQL injection by construction).
- Every endpoint that touches organization-scoped data must filter by the authenticated user's `organization_id` at the query level — never rely on the frontend to only *ask* for the right org's data.
- Secrets (DB URL, LLM API keys, JWT signing key) live in environment variables, never in source. A `.env.example` file documents required variables without real values.

### Frontend (React)
- Functional components with hooks only — no class components.
- API calls go through a single typed client layer, not scattered `fetch` calls across components.
- Loading and error states are required for every async view, not optional polish — the extraction step is asynchronous by design (`TRD.md` FR-1.6) and a UI with no loading state will look broken.

### Database
- Every schema change goes through an Alembic migration — never a manual edit against a running database, including the free-tier dev database.
- Foreign keys are enforced at the database level, not just assumed at the application level.

### AI/LLM Pipeline Code
- LLM calls are isolated behind a single provider-agnostic interface (e.g., `extract_clause(text) -> ExtractionResult`) so swapping Groq for Gemini or Ollama (per `TRD.md`, Section 2.3) is a configuration change, not a rewrite.
- Every LLM call site has a timeout and a defined failure behavior (mark document "extraction failed, retry") — never let a hung API call block the request queue.
- Prompts are stored as versioned template files, not inlined as ad-hoc strings scattered through the codebase — makes prompt changes reviewable in a diff.

---

## Part C — Git & Workflow Rules

- **Branching:** `main` is always deployable. Feature work happens on `feature/<short-description>` branches.
- **Commits:** written in imperative mood ("Add clause verification endpoint", not "Added" or "Adding"); one logical change per commit where practical.
- **Never commit:** `.env` files, real contract samples used for manual testing, API keys, or database dump files.
- **Pull requests (even solo):** use PRs against `main` rather than direct pushes for anything beyond a trivial fix — it creates a reviewable history and a natural point to run CI.

## Part D — Documentation Rules

- When a decision changes something recorded in `PRD.md`, `TRD.md`, or `constraint.md`, update that document in the same change — don't let the docs drift from what the code actually does.
- Update `blueprint.md`'s phase/status tracking as phases complete, so the document stays a reliable source of "what's actually built" rather than "what was originally planned."
