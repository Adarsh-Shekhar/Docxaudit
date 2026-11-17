/** Viewer tests (Phase 17.6): DOCX text view highlights; PDF viewer overlay
 * with react-pdf mocked; page-sync behavior. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import TextViewer, { buildSegments } from "@/components/TextViewer";
import DocumentViewer from "@/components/DocumentViewer";
import type { ClauseResponse } from "@/types/api";

// react-pdf mocked: Document renders children, Page renders a sized box.
vi.mock("react-pdf", () => ({
  Document: ({ children }: { children: React.ReactNode }) => <div data-testid="pdf-document">{children}</div>,
  Page: ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid="pdf-page" data-page={pageNumber} style={{ width: 612, height: 792 }} />
  ),
  pdfjs: { GlobalWorkerOptions: { workerSrc: "" } },
}));

vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "/worker.mjs" }));

function clause(overrides: Partial<ClauseResponse>): ClauseResponse {
  return {
    id: overrides.id ?? "c1",
    document_id: "d1",
    obligation_type: "renewal",
    plain_language_text: "summary",
    raw_source_text: "source",
    page_number: 1,
    char_start: 0,
    char_end: 0,
    confidence_score: 0.8,
    status: "pending",
    created_at: "2026-01-01T00:00:00Z",
    bbox: { page_number: 1, x0: 72, y0: 500, x1: 400, y1: 520 },
    ...overrides,
  };
}

describe("buildSegments (DOCX span mapping)", () => {
  it("marks exactly the clause span within the full text", () => {
    const text = "Intro paragraph.\nClause one about renewal.\nClosing text.";
    // "Intro paragraph." (16) + "\n" → clause starts at 17, is 25 chars long.
    const clauses = [clause({ id: "a", char_start: 17, char_end: 42 })];
    const segments = buildSegments(text, clauses);
    const marked = segments.filter((s) => s.clause !== null).map((s) => s.content);
    expect(marked).toEqual(["Clause one about renewal."]);
    expect(marked[0]).toBe(text.slice(17, 42));
  });

  it("handles empty clause lists and out-of-range spans", () => {
    expect(buildSegments("hello", [])).toEqual([{ content: "hello", clause: null }]);
    const bad = [clause({ char_start: 100, char_end: 200 })];
    expect(buildSegments("hello", bad)).toEqual([{ content: "hello", clause: null }]);
  });
});

describe("TextViewer (DOCX)", () => {
  const text = "Intro paragraph.\nClause one about renewal.\nClosing text.";

  it("renders an inline highlight for the selected clause", () => {
    const c = clause({ id: "a", char_start: 17, char_end: 42 });
    render(
      <TextViewer text={text} clauses={[c]} selectedClause={c} onSelectClause={vi.fn()} />,
    );
    const mark = screen.getByTestId("text-highlight-a");
    expect(mark).toHaveTextContent("Clause one about renewal.");
    expect(mark).toHaveAttribute("data-selected", "true");
  });

  it("clicking a highlight selects the clause (17.3)", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const c = clause({ id: "a", char_start: 17, char_end: 42 });
    render(
      <TextViewer text={text} clauses={[c]} selectedClause={null} onSelectClause={onSelect} />,
    );
    await user.click(screen.getByTestId("text-highlight-a"));
    expect(onSelect).toHaveBeenCalledWith(c);
  });
});

describe("DocumentViewer (PDF)", () => {
  const bytes = new Uint8Array([1, 2, 3]);
  const clauses = [
    clause({ id: "page1", page_number: 1 }),
    clause({ id: "page2", page_number: 2 }),
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the pdf page and only that page's highlights", async () => {
    render(
      <DocumentViewer
        fileData={bytes}
        clauses={clauses}
        selectedClause={null}
        onSelectClause={vi.fn()}
      />,
    );
    expect(await screen.findByTestId("pdf-page")).toHaveAttribute("data-page", "1");
    expect(screen.getByTestId("highlight-page1")).toBeInTheDocument();
    expect(screen.queryByTestId("highlight-page2")).not.toBeInTheDocument();
  });

  it("positions the highlight overlay from the bbox percentages", () => {
    render(
      <DocumentViewer
        fileData={bytes}
        clauses={[clause({ id: "page1" })]}
        selectedClause={null}
        onSelectClause={vi.fn()}
      />,
    );
    const highlight = screen.getByTestId("highlight-page1");
    // bbox x0=72/612 ≈ 11.765% left, (400-72)/612 ≈ 53.595% width (as % strings).
    expect(parseFloat(highlight.style.left)).toBeCloseTo(11.7647, 3);
    expect(parseFloat(highlight.style.width)).toBeCloseTo(53.5948, 3);
  });

  it("clicking a highlight selects its clause (17.3)", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <DocumentViewer
        fileData={bytes}
        clauses={[clause({ id: "page1" })]}
        selectedClause={null}
        onSelectClause={onSelect}
      />,
    );
    await user.click(screen.getByTestId("highlight-page1"));
    expect(onSelect).toHaveBeenCalledWith(clauses[0]);
  });
});
