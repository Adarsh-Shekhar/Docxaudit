/** Routing (Phase 14.4) — public vs protected routes with an auth guard. */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AppShell } from "@/components/layout/AppShell";
import { FullPageLoader } from "@/components/FullPageLoader";

/** Redirects unauthenticated users to login, remembering where they were. */
export function RequireAuth() {
  const { isAuthenticated, initialized } = useAuth();
  const location = useLocation();

  if (!initialized) {
    return <FullPageLoader />;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

/** Logged-in users skip the auth pages. */
export function RedirectIfAuthenticated() {
  const { isAuthenticated, initialized } = useAuth();
  if (!initialized) {
    return <FullPageLoader />;
  }
  if (isAuthenticated) {
    return <Navigate to="/documents" replace />;
  }
  return <Outlet />;
}
