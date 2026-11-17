/** Documents page (Phase 16.2/16.3/16.4/16.5): org document list, upload,
 * extraction trigger + 2s polling until terminal state, error + retry. */
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listDocuments, triggerExtraction, getExtractionStatus } from "@/api/documents";
import { errorMessage } from "@/api/client";
import type { DocumentResponse, ExtractionStatus } from "@/types/api";
import { DocumentUpload } from "@/components/DocumentUpload";
import { EmptyState, ErrorState } from "@/components/ErrorState";
import { InlineSpinner } from "@/components/FullPageLoader";

const RUNNING: ReadonlySet<ExtractionStatus> = new Set([
  "queued",
  "parsing",
  "filtering",
  "extracting",
  "scoring",
  "persisting",
]);

export function statusBadgeClass(status: ExtractionStatus): string {
  if (status === "completed") return "bg-green-100 text-green-800";
  if (status === "failed") return "bg-red-100 text-red-800";
  if (status === "not_started") return "bg-slate-100 text-slate-600";
  return "bg-blue-100 text-blue-800"; // any running/queued state
}

function ExtractionStatusBadge({ documentId }: { documentId: string }) {
  const { data } = useQuery({
    queryKey: ["extraction-status", documentId],
    queryFn: () => getExtractionStatus(documentId),
    // Poll every 2s while the pipeline runs (Phase 16.3); stop on terminal.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && RUNNING.has(status) ? 2_000 : false;
    },
  });
  if (!data) return <InlineSpinner label="Checking status…" />;
  return (
    <span data-testid={`status-${documentId}`} className="flex flex-col items-start gap-0.5">
      <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusBadgeClass(data.status)}`}>
        {data.status}
      </span>
      {data.progress && RUNNING.has(data.status) && data.progress.total > 0 && (
        <span className="text-xs text-slate-500">
          Extracting clause {Math.max(1, data.progress.done)} of {data.progress.total}
        </span>
      )}
      {data.status === "failed" && data.error && (
        <span className="max-w-xs truncate text-xs text-red-700" title={data.error}>
          {data.error}
        </span>
      )}
    </span>
  );
}

function DocumentRow({ document: doc }: { document: DocumentResponse }) {
  const queryClient = useQueryClient();
  const extract = useMutation({
    mutationFn: () => triggerExtraction(doc.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["extraction-status", doc.id] });
    },
  });

  return (
    <tr className="border-b border-slate-100" data-testid="document-row">
      <td className="px-4 py-3">
        <Link to={`/documents/${doc.id}`} className="font-medium text-slate-800 hover:underline">
          {doc.filename}
        </Link>
        <div className="text-xs text-slate-500">
          v{doc.version} · {doc.mime_type === "application/pdf" ? "PDF" : "DOCX"}
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(doc.uploaded_at).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        <ExtractionStatusBadge documentId={doc.id} />
      </td>
      <td className="px-4 py-3 text-right">
        <button
          type="button"
          onClick={() => extract.mutate()}
          disabled={extract.isPending}
          data-testid={`extract-${doc.id}`}
          className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {extract.isPending ? "Starting…" : "Extract"}
        </button>
        <Link
          to={`/documents/${doc.id}`}
          className="ml-2 rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Review
        </Link>
      </td>
    </tr>
  );
}

export default function DocumentsPage(): ReactNode {
  const queryClient = useQueryClient();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  if (documents.isLoading) {
    return <InlineSpinner label="Loading documents…" />;
  }
  if (documents.isError) {
    return (
      <ErrorState
        message={errorMessage(documents.error)}
        onRetry={() => void documents.refetch()}
      />
    );
  }

  const docs = documents.data ?? [];

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Documents</h1>
        <button
          type="button"
          onClick={() => setShowUpload((open) => !open)}
          data-testid="toggle-upload"
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          {showUpload ? "Close" : "Upload document"}
        </button>
      </div>

      {showUpload && (
        <div className="mb-6">
          <DocumentUpload
            onUploaded={() => {
              setShowUpload(false);
              void queryClient.invalidateQueries({ queryKey: ["documents"] });
            }}
            onError={setUploadError}
          />
          {uploadError && (
            <p role="alert" data-testid="upload-error" className="mt-2 text-sm text-red-600">
              {uploadError}
            </p>
          )}
        </div>
      )}

      {docs.length === 0 ? (
        <EmptyState title="No documents yet" hint="Upload your first contract to get started." />
      ) : (
        <table className="w-full rounded-lg border border-slate-200 text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <th className="px-4 py-2">Document</th>
              <th className="px-4 py-2">Uploaded</th>
              <th className="px-4 py-2">Extraction</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <DocumentRow key={doc.id} document={doc} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
