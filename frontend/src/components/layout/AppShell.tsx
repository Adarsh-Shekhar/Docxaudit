/** App shell (Phase 14.5): nav, org name, user menu, and the persistent
 * disclaimer banner (R-1) — non-dismissible by default: it appears on every
 * authenticated page, since every summary is descriptive, never a legal
 * conclusion. */
import { useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useQueryClient } from "@tanstack/react-query";

function DisclaimerBanner() {
  return (
    <div
      role="note"
      data-testid="disclaimer-banner"
      className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900"
    >
      ⚠️ This tool provides automated, plain-language summaries only. It is not legal advice. Every
      entry traces to the source text — always verify against the original document before acting.
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, org, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    queryClient.clear();
    void navigate("/login");
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded text-sm ${isActive ? "bg-slate-200 font-semibold" : "hover:bg-slate-100"}`;

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <DisclaimerBanner />
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-4">
          <Link to="/documents" className="text-lg font-bold text-slate-900">
            Obligation Tracker
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/documents" className={navLinkClass}>
              Documents
            </NavLink>
          </nav>
        </div>
        <div className="relative">
          <button
            type="button"
            data-testid="user-menu-button"
            onClick={() => setMenuOpen((open) => !open)}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm hover:bg-slate-100"
          >
            <span className="font-medium">{user?.email ?? "…"}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs uppercase text-slate-600">
              {user?.role ?? "…"}
            </span>
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-1 w-48 rounded border border-slate-200 bg-white py-1 shadow-lg">
              <div className="border-b border-slate-100 px-3 py-2 text-xs text-slate-500">
                {org?.name ?? ""}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                data-testid="logout-button"
                className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
