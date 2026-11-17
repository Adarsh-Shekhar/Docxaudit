/** Document content helper: backend returns base64 JSON → raw bytes for
 * react-pdf (Phase 17). */
import { downloadDocument } from "@/api/documents";

export function base64ToUint8Array(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export async function fetchDocumentBytes(documentId: string): Promise<Uint8Array> {
  const blob = await downloadDocument(documentId);
  const buffer = await blob.arrayBuffer();
  const payload = JSON.parse(new TextDecoder().decode(buffer)) as { content_base64: string };
  return base64ToUint8Array(payload.content_base64);
}
