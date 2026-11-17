/** PDF viewer with highlight overlay (Phase 17.1/17.2/17.3/17.5).
 *
 * Uses react-pdf (pdf.js) with a Vite-imported worker. Pages are paginated
 * (prev/next + jump) rather than rendering all pages at once — keeps the
 * viewer responsive during extraction polling (17.5) and avoids needing a
 * virtualization library at this scale.
 *
 * Highlights (17.2): clause bbox values are in PDF points; the overlay is
 * positioned in percentages of the page so it stays correct at any zoom.
 */
import { useMemo, useState, type ReactNode } from "react";import { Document, Page, pdfjs } from "react-pdf";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { ClauseResponse } from "@/types/api";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

/**
 * Letter-size assumption (612×792 pt) for percentage positioning. Most
 * contracts are letter/A4; a follow-up can read the real page viewport
 * from pdf.js and pass exact page dimensions per page.
 */
export const PAGE_WIDTH_FALLBACK = 612;
export const PAGE_HEIGHT_FALLBACK = 792;

interface DocumentViewerProps {
  fileData: Uint8Array;
  clauses: ClauseResponse[];
  selectedClause: ClauseResponse | null;
  onSelectClause: (clause: ClauseResponse) => void;
}

export default function DocumentViewer({
  fileData,
  clauses,
  selectedClause,
  onSelectClause,
}: DocumentViewerProps): ReactNode {
  const [pageCount, setPageCount] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);

  // Jump to the selected clause's page and highlight (Phase 17.3).
  // Render-time sync pattern (react.dev/learn/you-might-not-need-an-effect):
  // adjust state when a *new* clause is selected, without an effect.
  const [syncedClauseId, setSyncedClauseId] = useState<string | null>(null);
  const selectedPage = selectedClause?.page_number ?? null;
  if (selectedPage !== null && selectedClause !== null && selectedClause.id !== syncedClauseId) {
    setSyncedClauseId(selectedClause.id);
    setPageNumber(selectedPage);
  }

  const clausesOnPage = useMemo(
    () => clauses.filter((c) => c.page_number === pageNumber && c.bbox),
    [clauses, pageNumber],
  );

  const goTo = (page: number) => setPageNumber(Math.min(Math.max(1, page), pageCount || 1));

  return (
    <div data-testid="pdf-viewer" className="flex flex-col gap-2">
      <div className="flex items-center justify-between rounded border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm">
        <button
          type="button"
          onClick={() => goTo(pageNumber - 1)}
          disabled={pageNumber <= 1}
          data-testid="prev-page"
          className="rounded px-2 py-1 hover:bg-slate-200 disabled:opacity-40"
        >
          ← Prev
        </button>
        <span>
          Page {pageNumber} of {pageCount || "…"}
        </span>
        <button
          type="button"
          onClick={() => goTo(pageNumber + 1)}
          disabled={pageNumber >= pageCount}
          data-testid="next-page"
          className="rounded px-2 py-1 hover:bg-slate-200 disabled:opacity-40"
        >
          Next →
        </button>
      </div>

      <div className="max-h-[70vh] overflow-auto rounded border border-slate-200 p-2">
        <Document
          file={{ data: fileData }}
          onLoadSuccess={({ numPages }: { numPages: number }) => setPageCount(numPages)}
          loading={<p className="p-6 text-center text-sm text-slate-500">Loading PDF…</p>}
          error={<p className="p-6 text-center text-sm text-red-600">Could not render this PDF.</p>}
        >
          <div className="relative mx-auto w-fit">
            <Page
              pageNumber={pageNumber}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              loading={null}
            />
            {/* Highlight overlay (17.2/17.3): percentages of the page box. */}
            {clausesOnPage.map((clause) => {
              const box = clause.bbox!;
              return (
                <button
                  key={clause.id}
                  type="button"
                  aria-label={`Select clause: ${clause.plain_language_text.slice(0, 60)}`}
                  data-testid={`highlight-${clause.id}`}
                  data-selected={selectedClause?.id === clause.id}
                  onClick={() => onSelectClause(clause)}
                  className={`absolute cursor-pointer rounded-sm border transition-colors ${
                    selectedClause?.id === clause.id
                      ? "border-amber-500 bg-amber-300/50"
                      : "border-amber-300/60 bg-amber-200/30 hover:bg-amber-200/60"
                  }`}
                  style={{
                    left: `${(box.x0 / PAGE_WIDTH_FALLBACK) * 100}%`,
                    top: `${(box.y0 / PAGE_HEIGHT_FALLBACK) * 100}%`,
                    width: `${((box.x1 - box.x0) / PAGE_WIDTH_FALLBACK) * 100}%`,
                    height: `${((box.y1 - box.y0) / PAGE_HEIGHT_FALLBACK) * 100}%`,
                  }}
                />
              );
            })}
          </div>
        </Document>
      </div>
    </div>
  );
}
