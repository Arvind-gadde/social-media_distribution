/**
 * Redirect sanitizers — prevent open-redirect / javascript: URL injection when a
 * URL came from user input, a query param, or an API response.
 */

/**
 * Return `url` only if it is a safe SAME-ORIGIN path (starts with a single "/",
 * not "//" and not a scheme-relative or absolute URL). Otherwise `fallback`.
 */
export function safeInternalUrl(url: string | null | undefined, fallback: string): string {
  if (!url || typeof url !== 'string') return fallback;
  const trimmed = url.trim();
  // Must be a rooted path, but not protocol-relative ("//evil.com") or a
  // backslash trick, and must not contain a scheme.
  if (!trimmed.startsWith('/')) return fallback;
  if (trimmed.startsWith('//') || trimmed.startsWith('/\\')) return fallback;
  if (/^\/+[a-z][a-z0-9+.-]*:/i.test(trimmed)) return fallback;
  return trimmed;
}

/**
 * Return `url` only if it is an absolute https URL (e.g. a Stripe Checkout link).
 * Rejects http, javascript:, data:, and malformed URLs. Otherwise `fallback`.
 */
export function safeRedirectUrl(url: string | null | undefined, fallback: string): string {
  if (!url || typeof url !== 'string') return fallback;
  try {
    const parsed = new URL(url.trim());
    if (parsed.protocol !== 'https:') return fallback;
    return parsed.toString();
  } catch {
    return fallback;
  }
}
