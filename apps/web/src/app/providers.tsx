'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from 'next-themes';
import { getQueryClient } from '@/lib/query-client';
import { useState, type ReactNode } from 'react';
import { restoreApiClientFromStorage } from '@/lib/api';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(() => getQueryClient());

  // Hydrate the access token from localStorage SYNCHRONOUSLY on the client,
  // before any child component mounts and fires an authenticated query. Doing
  // this in a post-paint useEffect raced the first render on a hard reload:
  // queries read a null token, got a 401, and the handler force-logged-out.
  // restoreApiClientFromStorage is a no-op on the server.
  useState(() => {
    restoreApiClientFromStorage();
    return null;
  });

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        {children}
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
