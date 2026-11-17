# Deployment Guide (Phase 6 — free-tier pipeline proof)

Goal: prove the zero-cost pipeline end-to-end with the (now real) app: Neon + Render + Vercel/Cloudflare, before building on top of it (constraint C-2).

> Accounts needed: GitHub (repo), Neon, Render, Vercel **or** Cloudflare Pages, Groq, Gemini (fallback), Resend.

## 0. Prereqs on your machine

1. Root `.env` filled from `.env.example` (Neon URL, Groq key, Resend key; JWT secret).
2. GitHub repo created and added: `git remote add origin <url> && git push -u origin main`.

## 1. Neon (database)

1. Create a project (e.g., `obligation-tracker-dev`).
2. Copy the connection string (`postgresql://...neon.tech/neondb?sslmode=require`) → `DATABASE_URL`.
3. Run migrations from your machine:
   ```powershell
   .\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
   ```
   (Phase 3.7/6.1.) Verify tables in the Neon SQL editor: `\dt` equivalent → 9 tables + `alembic_version`.

## 2. Render (backend)

1. New → Web Service → connect the GitHub repo.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3.12 (Render image; matches CI)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - No Dockerfile needed (0.1 decision — deferred).
3. Environment variables: copy every key from `.env` (DATABASE_URL, JWT_SECRET_KEY, GROQ_API_KEY, RESEND_API_KEY, FRONTEND_ORIGIN=**your Vercel URL**, LLM_PROVIDER=groq...).
4. Deploy → open `/health` → expect `{"status":"ok"}`.
5. Note the service URL (e.g., `https://obligation-tracker-api.onrender.com`).

**Cold start:** free instance spins down after ~15 min idle; first request takes a few seconds. Add "wake Render + run a Neon query" to any pre-demo checklist (plan §35).

## 3. Vercel / Cloudflare Pages (frontend)

1. New project → connect repo → Root Directory `frontend`.
2. Build: `npm run build` · Output: `dist`.
3. Environment variable: `VITE_API_BASE_URL=https://<render-url>`.
4. Deploy → note the URL → update Render's `FRONTEND_ORIGIN` env to this URL (CORS, Phase 6.4).

## 4. End-to-end proof (Phase 6 DoD)

From the deployed frontend: register → login → see dashboard. **No local services involved.**

Quick API-level check (substitute URLs):
```powershell
curl.exe -X POST https://<render>/auth/register -H "Content-Type: application/json" `
  -d '{"email":"you@example.com","password":"S3cure-passphrase","organization_name":"Acme"}'
```

## 5. Pre-demo warm-up (carry to Phase 35)

- [ ] Wake Render (`GET /health` until 200)
- [ ] Wake Neon (any query)
- [ ] Check Groq daily quota headroom
- [ ] Confirm Gemini fallback key valid
- [ ] Test email actually arrives (check spam)
