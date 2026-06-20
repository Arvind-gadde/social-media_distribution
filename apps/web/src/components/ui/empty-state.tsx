import * as React from 'react';
import { cn } from '@/lib/utils';

type FeaturedIconSize = 'sm' | 'md' | 'lg';
type FeaturedIconColor = 'brand' | 'gray' | 'success' | 'warning' | 'error' | 'info';

interface FeaturedIconProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: FeaturedIconSize;
  color?: FeaturedIconColor;
  icon: React.ReactNode;
}

const featuredSizeMap: Record<FeaturedIconSize, string> = {
  sm: 'h-10 w-10 ring-4',
  md: 'h-12 w-12 ring-[6px]',
  lg: 'h-14 w-14 ring-8',
};

const featuredIconSizeMap: Record<FeaturedIconSize, string> = {
  sm: '[&>svg]:h-5 [&>svg]:w-5',
  md: '[&>svg]:h-6 [&>svg]:w-6',
  lg: '[&>svg]:h-6 [&>svg]:w-6',
};

const featuredColorMap: Record<FeaturedIconColor, string> = {
  brand: 'bg-brand-100 ring-brand-50 text-brand-600 dark:bg-brand-900/40 dark:ring-brand-900/20 dark:text-brand-300',
  gray: 'bg-gray-100 ring-gray-50 text-gray-600 dark:bg-gray-800 dark:ring-gray-900/40 dark:text-gray-300',
  success:
    'bg-success-100 ring-success-50 text-success-600 dark:bg-success-900/40 dark:ring-success-900/20 dark:text-success-300',
  warning:
    'bg-warning-100 ring-warning-50 text-warning-600 dark:bg-warning-900/40 dark:ring-warning-900/20 dark:text-warning-300',
  error:
    'bg-error-100 ring-error-50 text-error-600 dark:bg-error-900/40 dark:ring-error-900/20 dark:text-error-300',
  info: 'bg-blue-100 ring-blue-50 text-blue-600 dark:bg-blue-900/40 dark:ring-blue-900/20 dark:text-blue-300',
};

const FeaturedIcon = React.forwardRef<HTMLDivElement, FeaturedIconProps>(
  ({ className, size = 'md', color = 'brand', icon, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center rounded-full',
        featuredSizeMap[size],
        featuredIconSizeMap[size],
        featuredColorMap[color],
        className
      )}
      aria-hidden
      {...props}
    >
      {icon}
    </div>
  )
);
FeaturedIcon.displayName = 'FeaturedIcon';

// ─── EmptyState ────────────────────────────────────────────────────────────

export interface EmptyStateProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  icon?: React.ReactNode;
  iconColor?: FeaturedIconColor;
  iconSize?: FeaturedIconSize;
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  (
    {
      className,
      icon,
      iconColor = 'brand',
      iconSize = 'lg',
      title,
      description,
      actions,
      children,
      ...props
    },
    ref
  ) => (
    <div
      ref={ref}
      className={cn('flex flex-col items-center justify-center text-center px-6 py-12', className)}
      {...props}
    >
      {icon && <FeaturedIcon icon={icon} color={iconColor} size={iconSize} className="mb-4" />}
      {title && (
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      )}
      {description && (
        <p className="mt-1 max-w-md text-sm text-gray-600 dark:text-gray-400">{description}</p>
      )}
      {children}
      {actions && <div className="mt-6 flex flex-wrap items-center justify-center gap-3">{actions}</div>}
    </div>
  )
);
EmptyState.displayName = 'EmptyState';

export { EmptyState, FeaturedIcon };
export type { FeaturedIconProps, FeaturedIconSize, FeaturedIconColor };
