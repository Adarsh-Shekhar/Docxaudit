/**
 * API type definitions mirroring backend Pydantic schemas (Phase 14.8).
 *
 * Keep in sync manually for v1 (consider OpenAPI codegen later — plan note).
 * Field names are camelCase on the frontend only where the backend uses
 * them; the backend uses snake_case, so we mirror it exactly to avoid a
 * mapping layer drifting out of sync.
 */

// ── auth ─────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: "admin" | "member";
  organization_id: string;
  created_at: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  organization_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ── documents ────────────────────────────────────────────────────────────────

export interface DocumentResponse {
  id: string;
  filename: string;
  mime_type: string;
  version: number;
  parent_document_id: string | null;
  uploaded_at: string;
}

export type ExtractionStatus =
  | "not_started"
  | "queued"
  | "parsing"
  | "filtering"
  | "extracting"
  | "scoring"
  | "persisting"
  | "completed"
  | "failed";

export interface ExtractionStatusResponse {
  status: ExtractionStatus;
  progress: { done: number; total: number } | null;
  error: string | null;
}

// ── clauses (Phase 13 API) ───────────────────────────────────────────────────

export type ObligationType =
  | "renewal"
  | "termination_notice"
  | "payment_trigger"
  | "evidence_compliance"
  | "other";

export type ClauseStatus = "pending" | "accepted" | "edited" | "rejected";

/** Bounding box in PDF points (x0, y0, x1, y1) — Phase 17.2 decision. */
export interface BBox {
  page_number: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface ClauseResponse {
  id: string;
  document_id: string;
  obligation_type: ObligationType;
  plain_language_text: string;
  raw_source_text: string;
  page_number: number | null;
  char_start: number;
  char_end: number;
  confidence_score: number;
  status: ClauseStatus;
  created_at: string;
  /** Present for PDF clauses; null/absent for DOCX (text view instead). */
  bbox?: BBox | null;
}

export interface ReviewProgress {
  reviewed: number;
  total: number;
}

export interface ClauseListResponse {
  clauses: ClauseResponse[];
  progress: ReviewProgress;
}

export interface ClauseUpdateRequest {
  action: "accept" | "edit" | "reject";
  plain_language_text?: string;
  obligation_type?: ObligationType;
}

// ── API errors ───────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { message: string; current_status?: string } | Array<Record<string, unknown>>;
}
