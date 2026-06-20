import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'tertiary'
  | 'link-gray'
  | 'link-color'
  | 'destructive'
  | 'destructive-secondary'
  // Legacy aliases retained for backwards compatibility with existing pages.
  | 'default'
  | 'outline'
  | 'ghost'
  | 'link';

export type ButtonSize = 'sm' | 'md' | 'lg' | 'xl' | 'icon' | 'default' | 'xs';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  asChild?: boolean;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-600 text-white shadow-xs hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-500',
  secondary:
    'bg-white text-gray-700 border border-gray-300 shadow-xs hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-800',
  tertiary:
    'bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200',
  'link-gray':
    'h-auto p-0 text-gray-600 underline-offset-4 hover:text-gray-900 hover:underline dark:text-gray-400 dark:hover:text-gray-100',
  'link-color':
    'h-auto p-0 text-brand-700 underline-offset-4 hover:text-brand-800 hover:underline dark:text-brand-400 dark:hover:text-brand-300',
  destructive:
    'bg-error-600 text-white shadow-xs hover:bg-error-700',
  'destructive-secondary':
    'bg-white text-error-700 border border-error-300 shadow-xs hover:bg-error-50 dark:bg-gray-900 dark:text-error-400 dark:border-error-800 dark:hover:bg-error-950',
  // Legacy aliases — mapped to closest Untitled UI variant.
  default:
    'bg-brand-600 text-white shadow-xs hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-500',
  outline:
    'bg-white text-gray-700 border border-gray-300 shadow-xs hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-800',
  ghost:
    'bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200',
  link: 'h-auto p-0 text-brand-700 underline-offset-4 hover:text-brand-800 hover:underline dark:text-brand-400 dark:hover:text-brand-300',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-3.5 text-sm',
  lg: 'h-11 px-4 text-base',
  xl: 'h-12 px-5 text-base',
  icon: 'h-10 w-10 p-0',
  // Legacy size aliases
  default: 'h-10 px-3.5 text-sm',
  xs: 'h-8 px-2.5 text-xs',
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      asChild = false,
      disabled,
      leadingIcon,
      trailingIcon,
      children,
      type,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : 'button';
    const isLink =
      variant === 'link-gray' || variant === 'link-color' || variant === 'link';

    const base = cn(
      'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors',
      'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/24',
      'disabled:pointer-events-none disabled:opacity-50 select-none shrink-0',
      variantStyles[variant],
      !isLink && sizeStyles[size],
      isLink && size === 'icon' && 'h-auto w-auto',
      className
    );

    const content = (
      <>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          leadingIcon && <span className="inline-flex shrink-0">{leadingIcon}</span>
        )}
        {children}
        {!loading && trailingIcon && (
          <span className="inline-flex shrink-0">{trailingIcon}</span>
        )}
      </>
    );

    if (asChild) {
      return (
        <Comp ref={ref} className={base} {...props}>
          {content}
        </Comp>
      );
    }

    return (
      <button
        ref={ref}
        type={type ?? 'button'}
        disabled={disabled || loading}
        className={base}
        {...props}
      >
        {content}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
