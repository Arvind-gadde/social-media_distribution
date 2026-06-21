/**
 * Client-side session marker.
 *
 * The real auth tokens are HttpOnly cookies set by the backend; this non-HttpOnly
 * `cf_session` cookie is just a hint the Next.js edge middleware reads to decide
 * whether to allow a route or redirect to /login. It carries no secret.
 */
'use client';

const SESSION_COOKIE = 'cf_session';
// 30 days — matches the refresh-token lifetime; the middleware only checks presence.
const MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

/** Mark the session active after a successful login/register. */
export function markSessionActive(): void {
  if (typeof document === 'undefined') return;
  const secure = window.location.protocol === 'https:' ? ' Secure;' : '';
  document.cookie =
    `${SESSION_COOKIE}=1; Path=/; Max-Age=${MAX_AGE_SECONDS}; SameSite=Lax;${secure}`;
}

/** Clear the session marker on logout. */
export function clearSession(): void {
  if (typeof document === 'undefined') return;
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

/** Whether the session marker is currently set (client-only). */
export function isSessionActive(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.split('; ').some((c) => c.startsWith(`${SESSION_COOKIE}=`) && !c.endsWith('='));
}
