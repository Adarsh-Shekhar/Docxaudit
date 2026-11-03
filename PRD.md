# Product Requirements Document (PRD)
## Plain-Language Obligation Tracker

| Field | Value |
|---|---|
| **Project** | Plain-Language Obligation Tracker |
| **Domain** | Legal Technology (LegalTech) |
| **Document Type** | Product Requirements Document |
| **Status** | Draft v1.0 |
| **Companion Docs** | `TRD.md` (technical design) · `rules.md` (build & behavior rules) · `constraint.md` (limits) · `blueprint.md` (execution plan) |

---

## 1. Overview

The **Plain-Language Obligation Tracker** is a web application that reads service agreements and contracts, finds the obligations buried inside them (renewals, termination notices, evidence/compliance duties, payment triggers), rewrites those obligations in plain language with a citation back to the exact source text, and lets a human verify each one before it becomes a real, owned, trackable task with a due date and an alert.

The product exists to close one specific gap: small organizations sign contracts they do not have the staff to re-read every month, so obligations slip past unnoticed until a penalty, an auto-renewal, or a lapsed compliance item forces the issue.

---

## 2. Problem Statement

Small organizations — NGOs, early-stage startups, small businesses — routinely sign multi-page vendor, lease, insurance, and service agreements. These documents bury time-sensitive obligations (a 60-day notice-to-terminate clause, an annual insurance-certificate requirement, an auto-renewal date) inside dense legal paragraphs that no one revisits after signing.

Without a dedicated legal or compliance team, these organizations rely on manual calendar reminders (if any) or institutional memory. Both fail silently:

- **No single source of truth.** Obligations live inside PDFs scattered across email and shared drives, not in one place anyone can check.
- **No ownership.** Even when a deadline is known, it is rarely assigned to a specific person who is accountable for it.
- **No lead time.** Notice periods (e.g., "must terminate 90 days before renewal") require action *before* the deadline itself, and generic calendar reminders don't account for this.
- **No proof trail.** Obligations that require evidence (e.g., "vendor must submit a certificate of insurance annually") have no structured place to attach and confirm that evidence was actually provided.

Enterprise contract-lifecycle-management (CLM) suites solve this, but they are priced for enterprises, not for a 10–50 person organization managing a few dozen active agreements.

---

## 3. Vision & Goals

**Vision:** Give any small organization the obligation-tracking discipline of an enterprise legal team, without an enterprise budget or a legal background.

**Product Goals**

| Goal | Description |
|---|---|
| **G1 — Surface the hidden** | Automatically find obligation-bearing clauses in an uploaded contract and explain them in plain language, with an exact citation back to the source. |
| **G2 — Never trust blindly** | Keep a human in the loop for every extracted clause before it becomes a real obligation — this is a trust and accuracy product, not a fire-and-forget one. |
| **G3 — Make it someone's job** | Convert every verified obligation into a task with a named owner, a due date, and a place to prove it was done. |
| **G4 — Miss nothing** | Alert the right person early enough — respecting notice periods, not just due dates — that action is still possible. |

---

## 4. Target Users & Personas

| Persona | Role | Core Need |
|---|---|---|
| **Priya — Operations Manager** | Runs day-to-day operations at a ~40-person NGO; not a lawyer. | A single dashboard of every active contract's obligations, because she currently finds out about a lease renewal deadline when the landlord calls. |
| **Rahul — Startup Founder** | Signs SaaS, vendor, and contractor agreements regularly. | Wants to know *before* an auto-renewal locks him in for another year, without paying for a full CLM platform. |
| **Meera — Compliance Coordinator** | Responsible for collecting evidence (insurance certificates, audit confirmations, deliverable sign-offs) required by contracts. | A structured place to attach proof of compliance per obligation, with a record of who submitted what and when. |

All three personas share one constraint: no legal background, and no budget for one.

---

## 5. User Stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-1 | Operations Manager | upload a signed contract (PDF/DOCX) | the system can find its obligations for me instead of me re-reading it |
| US-2 | Operations Manager | see each extracted clause highlighted on the original document | I can trust the extraction because I can see exactly where it came from |
| US-3 | Operations Manager | accept, edit, or reject each extracted clause | nothing enters my obligation list that I haven't personally confirmed |
| US-4 | Compliance Coordinator | assign a verified obligation to a specific teammate with a due date | there's a named, accountable owner instead of a shared inbox nobody checks |
| US-5 | Compliance Coordinator | attach a file as evidence that an obligation was fulfilled | there's a record proving compliance if the vendor or auditor asks |
| US-6 | Startup Founder | see all upcoming obligations on a calendar | I get a top-down view without opening every contract |
| US-7 | Startup Founder | get an alert a configurable number of days before a notice deadline | I still have time to act, not just be informed after it's too late |
| US-8 | Any user | re-upload an amended version of a contract | the obligation list reflects the current agreement, not a stale one |
| US-9 | Org Admin | invite teammates and control who can verify vs. only view | access matches each person's actual responsibility |

---

## 6. Functional Requirements

### 6.1 FR-1 — Document Ingestion & Extraction Engine
- **FR-1.1** Accept PDF and DOCX uploads; reject unsupported formats with a clear error.
- **FR-1.2** Parse document text while preserving page number and character-offset metadata, so every extracted clause can be traced back to its exact location.
- **FR-1.3** Identify candidate obligation-bearing clauses across these categories: **renewal**, **termination/notice period**, **payment trigger**, **evidence/compliance duty**, **other**.
- **FR-1.4** For each candidate clause, generate: a plain-language summary, the obligation type, any extractable date(s) or notice period, and a citation (page + offset) to the source text.
- **FR-1.5** Attach a confidence signal to each extraction so low-confidence clauses can be visually flagged for closer review.
- **FR-1.6** Process a new upload asynchronously and show progress, since extraction is not instantaneous.

### 6.2 FR-2 — Interactive Verification UI
- **FR-2.1** Show the original document and the list of extracted clauses side-by-side.
- **FR-2.2** Highlight the source span in the original document when a user selects an extracted clause.
- **FR-2.3** Allow a user to **Accept**, **Edit** (the plain-language text or obligation type), or **Reject** each extracted clause.
- **FR-2.4** Persist nothing to the verified Obligations list until a human takes one of the above actions — extraction output is provisional by default (see `rules.md`, R-2).
- **FR-2.5** Show a document-level progress indicator (e.g., "6 of 9 clauses reviewed").

### 6.3 FR-3 — Task & Accountability Management
- **FR-3.1** Convert a verified obligation into a task with: title, description, due date, optional recurrence (e.g., annual), owner, and status (Open / In Progress / Done).
- **FR-3.2** Allow assigning a task owner from the organization's member list.
- **FR-3.3** Allow attaching one or more evidence files to a task as proof of completion.
- **FR-3.4** Maintain a simple audit trail per task (who changed what, and when).
- **FR-3.5** Allow filtering/searching tasks by status, owner, due date range, and source document.

### 6.4 FR-4 — Calendar & Alerting Module
- **FR-4.1** Provide a calendar view (month/week) plotting every task's due date.
- **FR-4.2** Allow a configurable alert lead time per task or obligation type (e.g., 30/14/7 days before due).
- **FR-4.3** Send alerts via email and an in-app notification center.
- **FR-4.4** Provide a "this week" / "overdue" digest view.
- **FR-4.5** Allow snoozing or dismissing an individual alert without affecting the underlying due date.

### 6.5 FR-5 — Organization, Auth & Access Control (cross-cutting)
- **FR-5.1** Support multiple users per organization with at least two roles: **Admin** (can verify clauses, manage members, edit anything) and **Member** (can be assigned tasks, attach evidence, view obligations).
- **FR-5.2** Standard email/password authentication with session/token expiry.
- **FR-5.3** Every obligation, task, and document is scoped to one organization; no cross-organization data access.

---

## 7. Non-Goals / Out of Scope (v1)

- Not a full Contract Lifecycle Management (CLM) suite — no e-signature, no contract drafting or redlining.
- **Not a substitute for legal advice.** All plain-language output is explicitly labeled as an aid to human review, not a legal opinion (see `rules.md`, R-1).
- Not designed for enterprise-scale document volumes (thousands of contracts) in v1 — this is a capstone-scope prototype for a small organization's active agreement set.
- No multi-language contract support in v1 — English-language contracts only.
- No native mobile app — responsive web only.
- No native Google/Outlook Calendar two-way sync in v1 (may be a stretch goal — see `blueprint.md`).

---

## 8. Success Metrics

| Metric | Target (validate during testing) |
|---|---|
| Extraction recall on notice/renewal/evidence clauses (against a manually labeled test set) | ≥ 85% |
| False-positive rate on extracted clauses (flagged as an obligation but isn't one) | ≤ 20%, since a human always verifies before anything is trusted |
| Average time to fully verify a 10–20 page contract | < 10 minutes |
| % of tasks completed before their due date (across a pilot period) | ≥ 90% |
| Alerts delivered with correct lead time | 100% (this is a correctness requirement, not an aspiration) |

These are prototype-stage benchmarks to validate against a labeled test set of real or representative contracts — not claims about current performance.

---

## 9. Assumptions & Dependencies

- Users have basic comfort with web applications; no legal training assumed or required.
- Contracts are primarily digital-native PDFs or DOCX files (not scanned images requiring OCR) in v1 — see `constraint.md` for the OCR stretch-goal note.
- One organization = one team using the tool together; no assumption of multi-organization enterprise rollout.
- The extraction engine depends on an LLM provider being reachable; see `TRD.md` for the primary/fallback provider design and `constraint.md` for what happens if it's unavailable.

---

## 10. Risks (Product-Level)

| Risk | Impact | Mitigation |
|---|---|---|
| Users over-trust AI-extracted clauses and skip verification | A missed obligation despite using the tool — the exact failure mode this product exists to prevent | Verification is mandatory by design (FR-2.4); nothing reaches the Obligations table unreviewed |
| Extraction misses an obligation entirely (false negative) | Silent gap, worse than not using the tool at all because of false confidence | Track recall explicitly (Section 8); surface a "document fully reviewed" checkpoint so gaps are a conscious human call, not a silent one |
| Users mistake plain-language summaries for legal advice | Reputational/legal exposure for the product and its users | Persistent, unmissable disclaimer (`rules.md`, R-1); summaries always paired with the source citation |
| Free-tier infrastructure limits are hit during a demo or pilot | Downtime at the worst possible moment | Documented explicitly in `constraint.md`, with a pre-demo checklist in `blueprint.md` |

---

## 11. Release Milestones (High-Level)

See `blueprint.md` for the detailed, phased build plan. At the product level:

1. **Alpha** — Upload → extract → verify → manual task creation works end-to-end for one document at a time.
2. **Beta** — Calendar, alerting, evidence attachments, and multi-user roles are live; recurring obligations supported.
3. **Demo/Final** — Polish, a small labeled test set for the accuracy metrics in Section 8, and a rehearsed demo script.

---

## 12. Open Questions

- Should recurring obligations (e.g., "annual insurance certificate") auto-regenerate next year's task on completion, or require a manual roll-over? *(Default assumption: auto-regenerate — confirm before Beta.)*
- Is OCR for scanned/image-based contracts in scope for this capstone cycle, or a documented stretch goal? *(Currently treated as out of scope — see `constraint.md`.)*
- What is the actual organization/pilot this will be tested against, if any, versus a synthetic test-contract set?
