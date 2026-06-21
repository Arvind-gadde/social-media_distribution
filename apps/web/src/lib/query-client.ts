/**
 * React Query client factory.
 *
 * Returns a fresh QueryClient per call — providers.tsx wraps it in
 * `useState(() => getQueryClient())`, giving one client per app mount (the
 * App-Router-safe pattern; never share a single client across SSR requests).
 */
import { QueryClient } from '@tanstack/react-query';

export function getQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
