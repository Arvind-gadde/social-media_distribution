/**
 * Web API client singleton.
 *
 * Wraps @contentflow/api-client with browser-specific token persistence:
 * - access token is mirrored to localStorage so it survives a hard reload
 * - a silent-refresh rotation re-persists the new token
 * - terminal 401 (no refresh possible) clears auth and bounces to /login
 */
'use client';

import { createApiClient, type ApiClient } from '@contentflow/api-client';

const ACCESS_TOKEN_KEY = 'access_token';
const SESSION_COOKIE = 'cf_session';

function persistToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch {
    /* storage may be unavailable (private mode) — ignore */
  }
}

function clearAuthAndRedirect(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch {
    /* ignore */
  }
  // Clear the session marker so middleware redirects on the next navigation.
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  // Avoid redirect loops if we're already on an auth page.
  if (!window.location.pathname.startsWith('/login') &&
      !window.location.pathname.startsWith('/register')) {
    window.location.href = '/login';
  }
}

export const apiClient: ApiClient = createApiClient({
  // Empty base URL -> requests hit same-origin `/api/...`, which Next rewrites
  // to the backend (keeps cookies same-site). Override via NEXT_PUBLIC_API_URL.
  baseURL: process.env.NEXT_PUBLIC_API_URL || '',
  onTokenRefreshed: persistToken,
  onTokenExpired: clearAuthAndRedirect,
});

/**
 * Synchronously hydrate the in-memory access token from localStorage. Must be
 * called on the client before the first authenticated query fires (see
 * providers.tsx). No-op on the server.
 */
export function restoreApiClientFromStorage(): void {
  if (typeof window === 'undefined') return;
  try {
    const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) apiClient.setAccessToken(token);
  } catch {
    /* ignore */
  }
}
