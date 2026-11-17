/**
 * Single typed API client (Phase 14.3) — ALL backend calls go through here
 * (rules Part B). JWT injection, 401 → refresh-once → logout handling.
 */
import axios, { AxiosError, type AxiosRequestConfig } from "axios";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

const TOKEN_KEY = "obt.access_token";
const REFRESH_KEY = "obt.refresh_token";

export const tokenStorage = {
  get access(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string): void {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// ── request: attach JWT ──────────────────────────────────────────────────────

api.interceptors.request.use((config) => {
  const token = tokenStorage.access;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── response: refresh once on 401, then give up ──────────────────────────────

let refreshing: Promise<string | null> | null = null;

async function tryRefresh(): Promise<string | null> {
  const refresh = tokenStorage.refresh;
  if (!refresh) return null;
  try {
    const resp = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh });
    const { access_token, refresh_token } = resp.data as { access_token: string; refresh_token: string };
    tokenStorage.set(access_token, refresh_token);
    return access_token;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retried && tokenStorage.refresh) {
      original._retried = true;
      refreshing = refreshing ?? tryRefresh();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` };
        return api.request(original);
      }
      tokenStorage.clear();
      window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);

/** Extract a human-readable message from an axios error (backend `detail`). */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      return first.msg ?? "Request failed";
    }
  }
  return "Something went wrong. Please try again.";
}
