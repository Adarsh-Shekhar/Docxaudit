/** Documents page tests (Phase 16.6) — upload validation, extraction
 * trigger + polling that stops on terminal status, error + retry. */
import { fireEvent, render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DocumentsPage from "@/pages/DocumentsPage";
import * as documentsApi from "@/api/documents";
import { useAuth } from "@/hooks/useAuth";
import type { ExtractionStatusResponse } from "@/types/api";

vi.mock("@/api/documents", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/documents")>();
  return {
    ...actual,
    listDocuments: vi.fn(),
    getExtractionStatus: vi.fn(),
    triggerExtraction: vi.fn(),
    uploadDocument: vi.fn(),
  };
});

const mockListDocuments = vi.mocked(documentsApi.listDocuments);
const mockGetStatus = vi.mocked(documentsApi.getExtractionStatus);
const mockTrigger = vi.mocked(documentsApi.triggerExtraction);
const mockUpload = vi.mocked(documentsApi.uploadDocument);

vi.mock("@/hooks/useAuth", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/useAuth")>()),
  useAuth: vi.fn(),
}));

const mockUseAuth = vi.mocked(useAuth);

const DOC = {
  id: "doc-1",
  filename: "contract.pdf",
  mime_type: "application/pdf",
  version: 1,
  parent_document_id: null,
  uploaded_at: "2026-01-01T00:00:00Z",
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  mockUseAuth.mockReturnValue({
    user: { id: "u1", email: "admin@example.com", role: "admin", organization_id: "o1", created_at: "" },
    org: { id: "o1", name: "Acme", created_at: "" },
    isAuthenticated: true,
    initialized: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("DocumentsPage", () => {
  it("renders empty state when there are no documents", async () => {
    mockListDocuments.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByTestId("empty-state")).toHaveTextContent("No documents yet");
  });

  it("rejects an unsupported file type client-side", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockListDocuments.mockResolvedValue([]);
    renderPage();

    await screen.findByTestId("empty-state"); // wait for the list to settle
    await user.click(await screen.findByTestId("toggle-upload"));
    const input = document.querySelector('input[data-testid="file-input"]') as HTMLInputElement;
    expect(input).not.toBeNull();

    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    // The input is visually hidden (click-through drop-zone); fire the change
    // event directly, exactly what a real file-picker selection dispatches.
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByTestId("upload-validation-error")).toHaveTextContent(
      "Only PDF or DOCX files are supported.",
    );
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("shows a running status while extracting and stops polling when completed", async () => {
    mockListDocuments.mockResolvedValue([DOC]);
    let calls = 0;
    mockGetStatus.mockImplementation(async (): Promise<ExtractionStatusResponse> => {
      calls += 1;
      if (calls <= 2) {
        return { status: "extracting", progress: { done: 1, total: 4 }, error: null };
      }
      return { status: "completed", progress: { done: 4, total: 4 }, error: null };
    });

    renderPage();
    const badge = await screen.findByTestId("status-doc-1");
    expect(badge).toHaveTextContent("extracting");
    expect(screen.getByText(/Extracting clause 1 of 4/)).toBeInTheDocument();

    // Advance past poll intervals until the terminal state arrives.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000);
    });
    await screen.findByText("completed");

    const callsAtTerminal = vi.mocked(documentsApi.getExtractionStatus).mock.calls.length;

    // After completion, polling stops — no further calls accrue.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_000);
    });
    expect(vi.mocked(documentsApi.getExtractionStatus).mock.calls.length).toBe(callsAtTerminal);
  });

  it("shows an error state with retry when the list fails", async () => {
    mockListDocuments.mockRejectedValue(new Error("offline"));
    renderPage();
    const error = await screen.findByTestId("error-state");
    expect(error).toHaveTextContent(/something went wrong/i);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("failed extraction shows the error and Extract acts as Retry", async () => {
    mockListDocuments.mockResolvedValue([DOC]);
    mockGetStatus.mockResolvedValue({
      status: "failed",
      progress: { done: 0, total: 0 },
      error: "LLM call failed after 3 attempts",
    });
    mockTrigger.mockResolvedValue({ status: "queued", progress: null, error: null });

    renderPage();
    const badge = await screen.findByTestId("status-doc-1");
    expect(badge).toHaveTextContent("failed");
    expect(screen.getByText(/LLM call failed/)).toBeInTheDocument();

    await userEvent
      .setup({ advanceTimers: vi.advanceTimersByTime })
      .click(screen.getByTestId("extract-doc-1"));
    await waitFor(() => expect(mockTrigger).toHaveBeenCalledWith("doc-1"));
  });
});
