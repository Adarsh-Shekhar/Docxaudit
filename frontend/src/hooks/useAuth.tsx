/**
 * Auth context (Phase 15.2/15.3/15.4).
 *
 * Token storage decision (documented): localStorage for v1 — simple, works
 * across tabs. Trade-off: vulnerable to XSS; httpOnly cookies are a
 * hardening stretch goal (plan §15.2). The app never evals untrusted
 * content, and the backend never renders user HTML, limiting exposure.
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { tokenStorage } from "@/api/client";
import * as authApi from "@/api/auth";
import type { UserResponse, OrganizationResponse } from "@/types/api";

interface AuthContextValue {
  user: UserResponse | null;
  org: OrganizationResponse | null;
  isAuthenticated: boolean;
  /** True once the initial session check (token present → load profile) finished. */
  initialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, organizationName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [org, setOrg] = useState<OrganizationResponse | null>(null);
  const [initialized, setInitialized] = useState(false);

  const hydrate = useCallback(async () => {
    if (!tokenStorage.access) {
      setUser(null);
      setOrg(null);
      return;
    }
    try {
      const [me, myOrg] = await Promise.all([authApi.getMe(), authApi.getMyOrg()]);
      setUser(me);
      setOrg(myOrg);
    } catch {
      // Invalid/expired tokens the interceptor could not refresh.
      tokenStorage.clear();
      setUser(null);
      setOrg(null);
    }
  }, []);

  // Initial session check.
  useMemo(() => {
    void hydrate().finally(() => setInitialized(true));
  }, [hydrate]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login({ email, password });
      tokenStorage.set(tokens.access_token, tokens.refresh_token);
      await hydrate();
    },
    [hydrate],
  );

  const register = useCallback(
    async (email: string, password: string, organizationName: string) => {
      const tokens = await authApi.register({
        email,
        password,
        organization_name: organizationName,
      });
      tokenStorage.set(tokens.access_token, tokens.refresh_token);
      await hydrate();
    },
    [hydrate],
  );

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
    setOrg(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      org,
      isAuthenticated: user !== null,
      initialized,
      login,
      register,
      logout,
    }),
    [user, org, initialized, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
