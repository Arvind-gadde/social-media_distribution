'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Untitled UI Toast
 *
 * Styled to match Untitled UI's notification pattern: rounded-xl card,
 * leading icon, title + description stack, close button.
 *
 * NOTE: This component preserves the public API used by `toaster.tsx`
 * (title/description/action/onClose props). Radix Toast primitives are
 * also exported for advanced consumers.
 */

const toastVariants = cva(
  cn(
    'pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden',
    'rounded-xl border p-4 pr-10 shadow-lg transition-all',
    'bg-white dark:bg-gray-900'
  ),
  {
    variants: {
      variant: {
        default: 'border-gray-200 dark:border-gray-800 text-gray-900 dark:text-gray-100',
        success: 'border-success-200 dark:border-success-800 text-gray-900 dark:text-gray-100',
        error: 'border-error-200 dark:border-error-800 text-gray-900 dark:text-gray-100',
        warning: 'border-warning-200 dark:border-warning-800 text-gray-900 dark:text-gray-100',
        info: 'border-blue-200 dark:border-blue-800 text-gray-900 dark:text-gray-100',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

const iconMap = {
  default: Info,
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const iconColorMap: Record<NonNullable<ToastProps['variant']>, string> = {
  default: 'text-gray-500',
  success: 'text-success-600',
  error: 'text-error-600',
  warning: 'text-warning-600',
  info: 'text-blue-600',
};

export interface ToastProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'>,
    VariantProps<typeof toastVariants> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  onClose?: () => void;
  hideIcon?: boolean;
}

const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  (
    { className, variant = 'default', title, description, action, onClose, hideIcon, ...props },
    ref
  ) => {
    const Icon = iconMap[variant ?? 'default'];
    return (
      <div
        ref={ref}
        role="status"
        aria-live="polite"
        className={cn(toastVariants({ variant }), className)}
        {...props}
      >
        {!hideIcon && (
          <div className="mt-0.5 shrink-0">
            <Icon className={cn('h-5 w-5', iconColorMap[variant ?? 'default'])} aria-hidden />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {title && (
            <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</div>
          )}
          {description && (
            <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</div>
          )}
          {action && <div className="mt-3 flex gap-2">{action}</div>}
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className={cn(
              'absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-md',
              'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300',
              'transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500'
            )}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }
);
Toast.displayName = 'Toast';

export { Toast, toastVariants };
