import api from "./client";
import type { User } from "../types";

export interface AuthResponse { user: User; }

export const getMe = () => api.get<AuthResponse>("/auth/me");
export const getGoogleUrl = () => api.get<{ url: string; state: string }>("/auth/google/url");
export const logout = () => api.post("/auth/logout");