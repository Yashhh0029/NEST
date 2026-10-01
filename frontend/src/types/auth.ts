import type { UserRole } from "./common";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  email_verified: boolean;
  email_verified_at?: string;
  created_at: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

export interface VerifyEmailResponse {
  message: string;
  email_verified: boolean;
}

export interface ResendVerificationResponse {
  message: string;
}
