# Constraints
## Plain-Language Obligation Tracker

This file lists everything that limits *how* the project can be built — the boundaries every decision in `PRD.md`, `TRD.md`, `rules.md`, and `blueprint.md` must fit inside. Where a constraint conflicts with a nice-to-have feature, the constraint wins.

---

## C-1 — Budget: Hard $0

**The project must run end-to-end at zero recurring cost.** Not "cheap" — zero. This is the single constraint that shapes every technology choice in `TRD.md`.

What this rules out:
- Any tool whose free tier requires a credit card *and* auto-bills past a usage threshold without an explicit, deliberate upgrade action.
- Paid LLM APIs (OpenAI, Anthropic, paid-only Claude/GPT tiers) as the *default* path — these can be discussed as future production upgrades, never assumed in the working build.
- Any managed service with no standing free tier (only a time-limited trial credit) as a load-bearing piece of the architecture — trial credits are fine for a throwaway experiment, not for the app you'll demo in week 12.

What this allows:
- Every tool in `TRD.md` Section 2, all standing free tiers or fully open-source, self-hostable software.
- Running components locally (Ollama, local Postgres via Docker) with no cloud cost at all during development.

**Rule of thumb:** if a decision requires typing in a credit card number to unlock the tier you actually need, that tool is disqualified as the default, even if the free tier looks generous today.

---

## C-2 — Timeline: Capstone/Academic Schedule

This document doesn't assume a specific submission date — fill in your actual milestones in `blueprint.md`. The constraint that matters regardless of exact dates:

- Development time is bounded by an academic term, shared with coursework and other obligations (per your existing workload — see `rules.md` for how this affects scope discipline).
- The build must reach a demoable state *before* the final deadline, with buffer for the free-tier cold-start and rate-limit quirks documented in `TRD.md` to surface and get fixed — don't leave first contact with Groq's daily cap or Render's spin-down for the night before a demo.
- Prefer a smaller feature set that works reliably over a larger one that's still being debugged at submission time. `blueprint.md` is phased specifically so there's always a working, demoable version at the end of each phase.

---

## C-3 — Team Size: Solo Development

This is being built by one person. Consequences:
- No architecture decision should assume a team to divide work across (e.g., no over-engineered microservice split — one FastAPI service is correct at this scale, not a limitation).
- Code review happens via self-review and PR discipline (`rules.md`, Part C), not a second engineer — lean on CI (tests, linting) to catch what a second pair of eyes normally would.
- Prioritize the phases in `blueprint.md` strictly in order. A solo timeline has no slack for building Phase 4 polish before Phase 2's core loop actually works end-to-end.

---

## C-4 — Hardware: Student-Class Compute

Assume development happens on a standard laptop, not a GPU workstation.

- **Local LLM inference (Ollama) is a documented option, not the default assumption.** Running a 7–8B parameter model locally is feasible on 16GB RAM without a dedicated GPU, but will be noticeably slower than Groq's hosted inference. Treat Ollama as the privacy-focused fallback (`rules.md` R-3), not the primary extraction path, unless your machine specifically has the RAM/GPU headroom to make it pleasant to develop against daily.
- Docker is assumed available for local Postgres/Redis during development — a reasonable assumption for a CS/Data Science capstone environment, but confirm before `blueprint.md` Phase 0 if working from an unfamiliar machine.

---

## C-5 — Free-Tier Infrastructure Ceilings

Summarized here as *limits to design around*; full rationale and current figures (checked September 2026) are in `TRD.md`, Section 2.

| Service | Hard ceiling | Practical consequence |
|---|---|---|
| Groq (LLM) | ~30 requests/min, daily caps vary by model | The candidate-filtering step (`TRD.md`, Section 3, Step 3) exists specifically to keep call volume under this ceiling — don't remove it to "simplify" the pipeline |
| Render (backend hosting) | 750 instance-hours/month, spins down after ~15 min idle | Cold start of a few seconds on the first request after idle — acceptable, but warm up before a live demo (see `blueprint.md` demo checklist) |
| Neon (database) | ~0.5 GB storage, ~100 compute-hours/month | Fine for a capstone-scale document/task volume; watch storage if you load a large synthetic test-contract set |
| Supabase (if used instead of Neon) | 500 MB DB, free project pauses after 7 days idle | Needs a manual dashboard restore after a long idle stretch — budget a few minutes before returning to it after a break |

**If a limit is actually hit:** switch to the documented fallback in `TRD.md` (Gemini for Groq, Oracle VM for Render) rather than reaching for a paid tier — that's the entire point of documenting fallbacks in the TRD.

---

## C-6 — Data Privacy & Legal Constraint

- Uploaded documents are real (or realistic) legal agreements. Treat them as sensitive by default — see `rules.md` R-3 for the concrete handling rules this implies.
- The product must never present its output as legal advice (`rules.md` R-1). This is as much a constraint as a hardware limit: it bounds what language and framing are acceptable anywhere in the UI, not just a disclaimer to bolt on at the end.
- If any real (not synthetic) third-party contracts are used for testing or the demo, confirm you have the right to use that content before uploading it to a third-party LLM API.

---

## C-7 — Scope Constraints (v1)

These mirror `PRD.md`'s Non-Goals, restated here as hard boundaries on effort:

- **Formats:** PDF and DOCX only. No OCR for scanned/image-based contracts in this cycle (a real, separate project in its own right).
- **Language:** English-language contracts only.
- **Scale:** Designed for a handful of organizations and a few dozen active contracts each — not production multi-tenant load. Free-tier infrastructure could not support enterprise scale even if the product design did.
- **Platform:** Responsive web only. No native mobile app.
- **Integrations:** No two-way Google/Outlook Calendar sync in v1 — the in-app calendar (FR-4.1) satisfies the core requirement without an external OAuth integration to build and maintain.

---

## C-8 — Academic Integrity

- Third-party libraries and any AI-assisted code generation used in the build should be usable/attributable in line with your institution's capstone policy — keep `TRD.md`'s dependency list (Section 9) current as the actual source of truth for "what's a dependency vs. what's original work."
- Sample/test contracts used during development and demo should be synthetic or clearly public-domain/permissively licensed, not real signed agreements belonging to a third party without permission (this is both an academic-integrity and a data-privacy constraint — see C-6).

---

## Constraint Summary Table

| ID | Constraint | Non-Negotiable? |
|---|---|---|
| C-1 | $0 recurring cost | Yes |
| C-2 | Fits within academic timeline | Yes |
| C-3 | Solo developer | Yes (current scope) |
| C-4 | Student-laptop-class hardware | Yes |
| C-5 | Free-tier infra ceilings (see table) | Design around, don't ignore |
| C-6 | No legal-advice framing; sensitive-document handling | Yes |
| C-7 | v1 feature scope boundaries | Revisit only via a `PRD.md` update |
| C-8 | Academic integrity in sourcing/attribution | Yes |
