/** DOCX text view (Phase 17.4) — pdf.js can't render DOCX, so the document
 * renders as its extracted text (the canonical string citation offsets
 * index into) with the selected clause's span highlighted inline.
 */
import { type ReactNode } from "react";
import type { ClauseResponse } from "@/types/api";

interface TextViewerProps {
  text: string;
  clauses: ClauseResponse[];
  selectedClause: ClauseResponse | null;
  onSelectClause: (clause: ClauseResponse) => void;
}

interface Segment {
  content: string;
  clause: ClauseResponse | null;
}

/** Split the text into highlighted / plain segments around clause spans. */
export function buildSegments(text: string, clauses: ClauseResponse[]): Segment[] {
  const spans = clauses
    .filter((c) => c.char_start >= 0 && c.char_end <= text.length && c.char_start < c.char_end)
    .sort((a, b) => a.char_start - b.char_start);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const clause of spans) {
    if (clause.char_start < cursor) continue; // overlapping span — keep first
    if (clause.char_start > cursor) {
      segments.push({ content: text.slice(cursor, clause.char_start), clause: null });
    }
    segments.push({ content: text.slice(clause.char_start, clause.char_end), clause });
    cursor = clause.char_end;
  }
  if (cursor < text.length) {
    segments.push({ content: text.slice(cursor), clause: null });
  }
  return segments;
}

export default function TextViewer({
  text,
  clauses,
  selectedClause,
  onSelectClause,
}: TextViewerProps): ReactNode {
  const segments = buildSegments(text, clauses);

  return (
    <div data-testid="text-viewer" className="max-h-[70vh] overflow-auto rounded border border-slate-200 bg-white p-6">
      <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-slate-800">
        {segments.map((segment, index) =>
          segment.clause ? (
            <mark
              key={index}
              data-testid={`text-highlight-${segment.clause.id}`}
              data-selected={selectedClause?.id === segment.clause.id}
              onClick={() => onSelectClause(segment.clause!)}
              className={`cursor-pointer rounded-sm px-0.5 transition-colors ${
                selectedClause?.id === segment.clause.id
                  ? "bg-amber-300"
                  : "bg-amber-100 hover:bg-amber-200"
              }`}
            >
              {segment.content}
            </mark>
          ) : (
            <span key={index}>{segment.content}</span>
          ),
        )}
      </pre>
    </div>
  );
}
