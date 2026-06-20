'use client';

import { useContext } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Compass, Home, Search } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { CommandBarContext } from '@/lib/command-bar-context';

export default function NotFound() {
  const router = useRouter();
  const commandBar = useContext(CommandBarContext);

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-12">
      <div className="w-full max-w-lg">
        <EmptyState
          icon={<Compass />}
          iconColor="brand"
          iconSize="lg"
          title="404 — page not found"
          description="The page you're looking for doesn't exist or has been moved. Check the URL or head back home."
          actions={
            <>
              <Button asChild size="lg" leadingIcon={<Home className="h-4 w-4" />}>
                <Link href="/">Back to dashboard</Link>
              </Button>
              <Button
                variant="secondary"
                size="lg"
                leadingIcon={<ArrowLeft className="h-4 w-4" />}
                onClick={() => router.back()}
              >
                Go back
              </Button>
            </>
          }
        />

        {commandBar && (
          <div className="mt-8 flex flex-col items-center gap-3 border-t border-gray-200 pt-8 dark:border-gray-800">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Looking for something specific?
            </p>
            <Button
              variant="tertiary"
              size="sm"
              leadingIcon={<Search className="h-3.5 w-3.5" />}
              onClick={() => commandBar.open()}
            >
              Open search (⌘K)
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
