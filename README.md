# Docxaudit

Docxaudit turns legal contracts into plain-language, source-cited obligations. Users review, accept, edit, or reject them, with the tool highlighting the exact source text for verification.

**Alerting, not daydreaming.** The pipeline flags candidate clauses → an LLM drafts summaries → a **human verifies every clause** before it becomes an obligation → obligations become owned, dated tasks with evidence, calendar, and email/in-app alerts.

> ⚠️ This tool does **not** provide legal advice. Everything extracted is descriptive ("this clause appears to require…") and must be verified by a human.

## Documentation

| Doc | Purpose |
|---|---|
| `PRD.md` | Product requirements |
| `TRD.md` | Technical design & stack |
| `constraint.md` | Governing constraints ($0 budget, free tiers, etc.) |
| `rules.md` | Behavioral + engineering + git rules |
| `implementation-plan.md` | Phase-by-phase execution plan |
| `blueprint.md` | Structure & status tracker |

## Tech stack (summary)

- **Frontend:** React (Vite) + Tailwind CSS + react-pdf + react-big-calendar + TanStack Query
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic + APScheduler
- **LLM:** API-only — Groq (Llama 3.3 70B) primary, Gemini Flash fallback. **No local LLM is installed.**
- **DB:** PostgreSQL via Neon (free tier) — used for both dev and prod (no Docker required)
- **Deploy:** Vercel/Cloudflare Pages (FE) + Render free web service (BE)
- **Email:** Resend free tier
- **Testing:** pytest · Vitest + RTL · Playwright · DuckDB (accuracy)

## Local development

### Backend

All Python work runs inside a project-local `.venv` (already created at the repo root):

```powershell
# Activate
.\.venv\Scripts\Activate.ps1

# Install deps
pip install -r backend/requirements.txt

# spaCy model (used by the candidate filter)
python -m spacy download en_core_web_sm

# Run
uvicorn app.main:app --reload
```

### Configuration

Copy `.env.example` to `.env` at the repo root and fill in:

- `DATABASE_URL` — your **Neon** connection string (used directly for local dev; no Docker)
- `GROQ_API_KEY` / `GEMINI_API_KEY` — LLM API keys (no local LLM)
- `RESEND_API_KEY` — email alert sender
- `JWT_SECRET_KEY` — long random string

Never commit `.env` or any key.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Git conventions

See `rules.md` Part C: `feature/<short-description>` branches, imperative commits, `main` always deployable. Never commit `.env`, real contract samples, API keys, or DB dumps.
