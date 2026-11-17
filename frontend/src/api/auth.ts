/** Auth endpoints (Phase 15). */
import { api } from "./client";
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse, OrganizationResponse } from "@/types/api";

export async function register(body: RegisterRequest): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/register", body);
  return data;
}

export async function login(body: LoginRequest): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken });
  return data;
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await api.get<UserResponse>("/users/me");
  return data;
}

export async function getMyOrg(): Promise<OrganizationResponse> {
  const { data } = await api.get<OrganizationResponse>("/orgs/me");
  return data;
}
