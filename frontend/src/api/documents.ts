/** Document + clause endpoints (Phases 16/17). */
import { api } from "./client";
import type {
  ClauseListResponse,
  ClauseResponse,
  ClauseUpdateRequest,
  DocumentResponse,
  ExtractionStatusResponse,
} from "@/types/api";

export async function listDocuments(): Promise<DocumentResponse[]> {
  const { data } = await api.get<DocumentResponse[]>("/documents");
  return data;
}

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
  replacesDocumentId?: string,
): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<DocumentResponse>("/documents", form, {
    params: replacesDocumentId ? { replaces_document_id: replacesDocumentId } : undefined,
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function triggerExtraction(documentId: string): Promise<ExtractionStatusResponse> {
  const { data } = await api.post<ExtractionStatusResponse>(`/documents/${documentId}/extract`);
  return data;
}

export async function getExtractionStatus(documentId: string): Promise<ExtractionStatusResponse> {
  const { data } = await api.get<ExtractionStatusResponse>(`/documents/${documentId}/status`);
  return data;
}

export async function listClauses(documentId: string): Promise<ClauseListResponse> {
  const { data } = await api.get<ClauseListResponse>(`/documents/${documentId}/clauses`);
  return data;
}

export async function decideClause(clauseId: string, decision: ClauseUpdateRequest): Promise<ClauseResponse> {
  const { data } = await api.patch<ClauseResponse>(`/clauses/${clauseId}`, decision);
  return data;
}

export async function getDocumentText(
  documentId: string,
): Promise<{ filename: string; mime_type: string; text: string }> {
  const { data } = await api.get(`/documents/${documentId}/text`);
  return data;
}

export async function downloadDocument(documentId: string): Promise<Blob> {
  const { data } = await api.get(`/documents/${documentId}/content`, { responseType: "blob" });
  return data as Blob;
}
