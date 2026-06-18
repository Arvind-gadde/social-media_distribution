/**
 * Application Providers
 * 
 * Wraps the app with necessary providers (React Query, etc.)
 */

'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { getQueryClient } from '@/lib/query-client';
import { useState, useEffect, type ReactNode } from 'react';
import { apiClient } from '@/lib/api';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Create query client once per component lifecycle
  const [queryClient] = useState(() => getQueryClient());

  // Initialize API client with token from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        apiClient.setAccessToken(token);
      }
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
