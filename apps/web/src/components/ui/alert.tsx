'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Info, CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const alertVariants = cva(
  'relative flex gap-3 p-4 rounded-xl border',
  {
    variants: {
      variant: {
        info: 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-900 text-blue-700 dark:text-blue-300',
        success:
          'bg-success-50 dark:bg-success-950/40 border-success-200 dark:border-success-900 text-success-700 dark:text-success-300',
        warning:
          'bg-warning-50 dark:bg-warning-950/40 border-warning-200 dark:border-warning-900 text-warning-700 dark:text-warning-300',
        error:
          'bg-error-50 dark:bg-error-950/40 border-error-200 dark:border-error-900 text-error-700 dark:text-error-300',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
);

type AlertVariant = NonNullable<VariantProps<typeof alertVariants>['variant']>;

const iconMap: Record<AlertVariant, React.ComponentType<{ className?: string }>> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: AlertCircle,
};

const iconColorMap: Record<AlertVariant, string> = {
  info: 'text-blue-600 dark:text-blue-400',
  success: 'text-success-600 dark:text-success-400',
  warning: 'text-warning-600 dark:text-warning-400',
  error: 'text-error-600 dark:text-error-400',
};

export interface AlertProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'>,
    VariantProps<typeof alertVariants> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  hideIcon?: boolean;
  onClose?: () => void;
  actions?: React.ReactNode;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      className,
      variant = 'info',
      title,
      description,
      icon,
      hideIcon,
      onClose,
      actions,
      children,
      ...props
    },
    ref
  ) => {
    const resolvedVariant: AlertVariant = variant ?? 'info';
    const Icon = iconMap[resolvedVariant];

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant: resolvedVariant }), className)}
        {...props}
      >
        {!hideIcon && (
          <div className="mt-0.5 shrink-0">
            {icon ?? <Icon className={cn('h-5 w-5', iconColorMap[resolvedVariant])} aria-hidden />}
          </div>
        )}

        <div className="flex-1 min-w-0">
          {title && <div className="text-sm font-semibold">{title}</div>}
          {description && (
            <div className={cn('text-sm', title ? 'mt-1 opacity-90' : 'opacity-95')}>
              {description}
            </div>
          )}
          {children}
          {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Dismiss"
            className={cn(
              'shrink-0 -mr-1 -mt-1 inline-flex h-7 w-7 items-center justify-center rounded-md',
              'opacity-70 hover:opacity-100 transition-opacity',
              'focus:outline-none focus:ring-2 focus:ring-current focus:ring-offset-1'
            )}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }
);
Alert.displayName = 'Alert';

const AlertTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h5 ref={ref} className={cn('text-sm font-semibold', className)} {...props} />
  )
);
AlertTitle.displayName = 'AlertTitle';

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm opacity-90', className)} {...props} />
));
AlertDescription.displayName = 'AlertDescription';

export { Alert, AlertTitle, AlertDescription, alertVariants };
