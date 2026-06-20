'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, Home, RefreshCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    if (process.env.NODE_ENV === 'production') {
      console.error('[Error boundary]', error);
    }
  }, [error]);

  const isDev = process.env.NODE_ENV === 'development';

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-12">
      <div className="w-full max-w-lg">
        <EmptyState
          icon={<AlertTriangle />}
          iconColor="error"
          iconSize="lg"
          title="Something went wrong"
          description="An unexpected error occurred. Our team has been notified. Try refreshing or return to the dashboard."
          actions={
            <>
              <Button
                onClick={reset}
                size="lg"
                leadingIcon={<RefreshCcw className="h-4 w-4" />}
              >
                Try again
              </Button>
              <Button
                asChild
                variant="secondary"
                size="lg"
                leadingIcon={<Home className="h-4 w-4" />}
              >
                <Link href="/">Dashboard</Link>
              </Button>
            </>
          }
        />

        {isDev && error?.message && (
          <div className="mt-8 max-h-40 overflow-auto rounded-lg border border-error-200 bg-error-50/60 p-4 text-left dark:border-error-900 dark:bg-error-950/30">
            <p className="whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-error-700 dark:text-error-300">
              {error.message}
            </p>
            {error.digest && (
              <p className="mt-2 font-mono text-[10px] text-gray-600 dark:text-gray-400">
                digest: {error.digest}
              </p>
            )}
          </div>
        )}

        {!isDev && error?.digest && (
          <p className="mt-6 text-center font-mono text-xs text-gray-600 dark:text-gray-400">
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}
