'use client';

import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type BadgeColor =
  | 'gray'
  | 'brand'
  | 'error'
  | 'warning'
  | 'success'
  | 'blue';

// Legacy variant names retained for backwards compatibility with existing pages.
export type BadgeVariant =
  | BadgeColor
  | 'default'
  | 'primary'
  | 'secondary'
  | 'info'
  | 'outline';

export type BadgeSize = 'sm' | 'md' | 'lg' | 'default';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  /** Alias of variant — Untitled UI calls this `color`. */
  color?: BadgeColor;
  size?: BadgeSize;
  dot?: boolean;
  leadingIcon?: React.ReactNode;
  onClose?: () => void;
}

const colorStyles: Record<BadgeColor, { bg: string; text: string; border: string; dot: string }> = {
  gray: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    text: 'text-gray-700 dark:text-gray-300',
    border: 'border-gray-200 dark:border-gray-700',
    dot: 'bg-gray-500',
  },
  brand: {
    bg: 'bg-brand-50 dark:bg-brand-950/60',
    text: 'text-brand-700 dark:text-brand-300',
    border: 'border-brand-200 dark:border-brand-800',
    dot: 'bg-brand-600',
  },
  error: {
    bg: 'bg-error-50 dark:bg-error-950/60',
    text: 'text-error-700 dark:text-error-300',
    border: 'border-error-200 dark:border-error-800',
    dot: 'bg-error-600',
  },
  warning: {
    bg: 'bg-warning-50 dark:bg-warning-950/60',
    text: 'text-warning-700 dark:text-warning-300',
    border: 'border-warning-200 dark:border-warning-800',
    dot: 'bg-warning-600',
  },
  success: {
    bg: 'bg-success-50 dark:bg-success-950/60',
    text: 'text-success-700 dark:text-success-300',
    border: 'border-success-200 dark:border-success-800',
    dot: 'bg-success-600',
  },
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-950/60',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    dot: 'bg-blue-600',
  },
};

const sizeStyles: Record<Exclude<BadgeSize, 'default'>, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const dotSizeStyles: Record<Exclude<BadgeSize, 'default'>, string> = {
  sm: 'h-1.5 w-1.5',
  md: 'h-2 w-2',
  lg: 'h-2 w-2',
};

function resolveColor(variant: BadgeVariant, color?: BadgeColor): BadgeColor {
  if (color) return color;
  switch (variant) {
    case 'primary':
      return 'brand';
    case 'info':
      return 'blue';
    case 'default':
    case 'secondary':
    case 'outline':
      return 'gray';
    default:
      return variant as BadgeColor;
  }
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant = 'gray',
      color,
      size = 'md',
      dot,
      leadingIcon,
      onClose,
      children,
      ...props
    },
    ref
  ) => {
    const resolved = resolveColor(variant, color);
    const styles = colorStyles[resolved];
    const sz = size === 'default' ? 'md' : size;

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1 rounded-full border font-medium transition-colors',
          styles.bg,
          styles.text,
          styles.border,
          sizeStyles[sz],
          className
        )}
        {...props}
      >
        {dot && (
          <span
            className={cn('inline-block rounded-full', dotSizeStyles[sz], styles.dot)}
            aria-hidden="true"
          />
        )}
        {!dot && leadingIcon && (
          <span className="inline-flex shrink-0 [&_svg]:h-3 [&_svg]:w-3" aria-hidden="true">
            {leadingIcon}
          </span>
        )}
        {children}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'ml-0.5 inline-flex shrink-0 items-center justify-center rounded-full p-0.5',
              'hover:bg-black/10 focus:outline-none focus:ring-2 focus:ring-current/40 dark:hover:bg-white/10'
            )}
            aria-label="Remove"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export { Badge };
