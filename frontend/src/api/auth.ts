import api from "./client";
import type { User } from "../types";

export interface AuthResponse {
  user: User;
  access_token?: string;  // returned from login/register/google — store in memory
}

export const getMe = () => api.get<AuthResponse>("/auth/me");
export const getGoogleUrl = () =>
  api.get<{ url: string; state: string }>("/auth/google/url");
export const logout = () => api.post("/auth/logout");

export const register = (data: {
  email: string;
  password: string;
  name: string;
}) => api.post<AuthResponse>("/auth/register", data);

export const loginWithPassword = (data: {
  email: string;
  password: string;
}) => api.post<AuthResponse>("/auth/login", data);