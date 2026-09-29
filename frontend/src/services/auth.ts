import { api, TOKEN_STORAGE_KEY } from "./api";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types/auth";

export const authService = {
  async register(payload: RegisterPayload): Promise<User> {
    const res = await api.post<User>("/api/auth/register", payload);
    return res.data;
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>("/api/auth/login", payload);
    const tokenData = res.data;
    if (tokenData?.access_token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, tokenData.access_token);
    }
    return tokenData;
  },

  async getMe(): Promise<User> {
    const res = await api.get<User>("/api/auth/me");
    return res.data;
  },

  logout(): void {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  },

  getToken(): string | null {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  },
};
