/** Document review page (Phase 17): two-pane layout — clause list (read-only
 * selection; accept/edit/reject actions + progress land in Phase 18) and the
 * document viewer (PDF with highlight overlay, DOCX as highlighted text). */
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listClauses } from "@/api/documents";
import { getDocumentText } from "@/api/documents";
import { fetchDocumentBytes } from "@/api/content";
import { errorMessage } from "@/api/client";
import type { ClauseResponse, ObligationType } from "@/types/api";
import { ErrorState, EmptyState } from "@/components/ErrorState";
import { InlineSpinner } from "@/components/FullPageLoader";
import DocumentViewer from "@/components/DocumentViewer";
import TextViewer from "@/components/TextViewer";

const TYPE_LABEL: Record<ObligationType, string> = {
  renewal: "Renewal",
  termination_notice: "Termination notice",
  payment_trigger: "Payment",
  evidence_compliance: "Evidence/compliance",
  other: "Other",
};

function ClauseListItem({
  clause,
  selected,
  onSelect,
}: {
  clause: ClauseResponse;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      data-testid={`clause-item-${clause.id}`}
      data-selected={selected}
      className={`w-full rounded border p-3 text-left transition-colors ${
        selected ? "border-slate-500 bg-slate-50" : "border-slate-200 hover:bg-slate-50"
      }`}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
          {TYPE_LABEL[clause.obligation_type] ?? clause.obligation_type}
        </span>
        <span className="text-xs text-slate-500">
          {clause.page_number !== null ? `p. ${clause.page_number}` : "§ text"}
          {" · "}
          {Math.round(clause.confidence_score * 100)}%
        </span>
      </div>
      <p className="line-clamp-3 text-sm text-slate-800">{clause.plain_language_text}</p>
    </button>
  );
}

export default function DocumentReviewPage(): ReactNode {
  const { documentId } = useParams<{ documentId: string }>();
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);

  const clauses = useQuery({
    queryKey: ["clauses", documentId],
    queryFn: () => listClauses(documentId!),
    enabled: documentId !== undefined,
  });

  const documentText = useQuery({
    queryKey: ["document-text", documentId],
    queryFn: () => getDocumentText(documentId!),
    enabled: documentId !== undefined,
  });

  const documentBytes = useQuery({
    queryKey: ["document-bytes", documentId],
    queryFn: () => fetchDocumentBytes(documentId!),
    enabled: documentId !== undefined,
    staleTime: Infinity,
  });

  if (clauses.isLoading || documentText.isLoading) {
    return <InlineSpinner label="Loading review…" />;
  }
  if (clauses.isError) {
    return <ErrorState message={errorMessage(clauses.error)} onRetry={() => void clauses.refetch()} />;
  }
  if (documentText.isError) {
    return (
      <ErrorState message={errorMessage(documentText.error)} onRetry={() => void documentText.refetch()} />
    );
  }

  const isPdf = (documentText.data?.mime_type ?? "").endsWith("pdf");
  const clauseList = clauses.data?.clauses ?? [];
  const selectedClause = clauseList.find((c) => c.id === selectedClauseId) ?? null;

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{documentText.data?.filename}</h1>
          <p className="text-xs text-slate-500">
            Click a clause to highlight its source span in the document.
          </p>
        </div>
        <Link to="/documents" className="text-sm text-slate-600 underline">
          ← All documents
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
        <aside className="flex max-h-[75vh] flex-col gap-2 overflow-auto pr-1">
          {clauseList.length === 0 ? (
            <EmptyState title="No clauses extracted yet" hint="Run extraction from the Documents page." />
          ) : (
            clauseList.map((clause) => (
              <ClauseListItem
                key={clause.id}
                clause={clause}
                selected={clause.id === selectedClauseId}
                onSelect={() => setSelectedClauseId(clause.id)}
              />
            ))
          )}
        </aside>

        <section>
          {isPdf ? (
            documentBytes.data ? (
              <DocumentViewer
                fileData={documentBytes.data}
                clauses={clauseList}
                selectedClause={selectedClause}
                onSelectClause={(clause) => setSelectedClauseId(clause.id)}
              />
            ) : documentBytes.isError ? (
              <ErrorState message={errorMessage(documentBytes.error)} onRetry={() => void documentBytes.refetch()} />
            ) : (
              <InlineSpinner label="Loading document…" />
            )
          ) : (
            <TextViewer
              text={documentText.data?.text ?? ""}
              clauses={clauseList}
              selectedClause={selectedClause}
              onSelectClause={(clause) => setSelectedClauseId(clause.id)}
            />
          )}
        </section>
      </div>
    </div>
  );
}
