'use client';

import * as React from 'react';
import { Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AuthLeftPanel } from '@/components/auth/AuthLeftPanel';

interface AuthShellProps {
  children: React.ReactNode;
  mounted: boolean;
}

export function AuthShell({ children, mounted }: AuthShellProps) {
  return (
    <div className="min-h-screen flex bg-white dark:bg-gray-950">
      <AuthLeftPanel />

      <div className="flex-1 relative flex flex-col items-center justify-center px-6 py-12 overflow-y-auto">
        {/* Mobile brand mark (hidden on lg, where AuthLeftPanel handles it) */}
        <div className="lg:hidden flex items-center gap-2 mb-8">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 shadow-sm">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div className="leading-tight">
            <p className="text-base font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              ContentFlow
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Publish once. Reach everywhere.
            </p>
          </div>
        </div>

        <div
          className={cn(
            'w-full max-w-sm transition-all duration-500',
            mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export function OrDivider() {
  return (
    <div className="relative my-6">
      <div className="absolute inset-0 flex items-center" aria-hidden="true">
        <div className="w-full border-t border-gray-200 dark:border-gray-800" />
      </div>
      <div className="relative flex justify-center">
        <span className="bg-white dark:bg-gray-950 px-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          OR
        </span>
      </div>
    </div>
  );
}
