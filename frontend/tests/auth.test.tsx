/** Login/Register UI tests (Phase 15.5) — api layer mocked, no backend. */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import { AuthProvider } from "@/hooks/useAuth";
import * as authApi from "@/api/auth";

vi.mock("@/api/auth", () => ({
  register: vi.fn(),
  login: vi.fn(),
  refreshTokens: vi.fn(),
  getMe: vi.fn(),
  getMyOrg: vi.fn(),
}));

const mockGetMe = vi.mocked(authApi.getMe);
const mockGetMyOrg = vi.mocked(authApi.getMyOrg);
const mockLogin = vi.mocked(authApi.login);
const mockRegister = vi.mocked(authApi.register);

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={ui} />
            <Route path="/documents" element={<div data-testid="documents-page">Documents</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const validUser = {
  id: "u1",
  email: "admin@example.com",
  role: "admin" as const,
  organization_id: "o1",
  created_at: "2026-01-01T00:00:00Z",
};
const validOrg = { id: "o1", name: "Acme", created_at: "2026-01-01T00:00:00Z" };

beforeEach(() => {
  vi.clearAllMocks();
  mockGetMe.mockResolvedValue(validUser);
  mockGetMyOrg.mockResolvedValue(validOrg);
});

describe("LoginPage", () => {
  it("shows validation errors for a bad email and empty password", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.click(screen.getByTestId("login-submit"));

    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("successful login stores tokens and redirects", async () => {
    mockLogin.mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "admin@example.com");
    await user.type(screen.getByLabelText("Password"), "longenough");
    await user.click(screen.getByTestId("login-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("documents-page")).toBeInTheDocument();
    });
    expect(mockLogin).toHaveBeenCalledWith({ email: "admin@example.com", password: "longenough" });
    expect(localStorage.getItem("obt.access_token")).toBe("a");
  });

  it("failed login shows the server error", async () => {
    mockLogin.mockRejectedValue(new Error("boom"));
    // errorMessage() for a plain Error returns the generic message.
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "admin@example.com");
    await user.type(screen.getByLabelText("Password"), "longenough");
    await user.click(screen.getByTestId("login-submit"));

    expect(await screen.findByTestId("login-error")).toHaveTextContent(/something went wrong/i);
  });
});

describe("RegisterPage", () => {
  it("rejects short passwords client-side", async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <MemoryRouter>
            <RegisterPage />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText("Organization name"), "Acme");
    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByTestId("register-submit"));

    expect(await screen.findByText("At least 8 characters.")).toBeInTheDocument();
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("registers and redirects on success", async () => {
    mockRegister.mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />);

    await user.type(screen.getByLabelText("Organization name"), "Acme");
    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "longenough");
    await user.click(screen.getByTestId("register-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("documents-page")).toBeInTheDocument();
    });
    expect(mockRegister).toHaveBeenCalledWith({
      email: "a@example.com",
      password: "longenough",
      organization_name: "Acme",
    });
  });
});
