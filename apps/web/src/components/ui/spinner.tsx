import * as React from 'react';
import { cn } from '@/lib/utils';

type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg';
type SpinnerColor = 'primary' | 'gray' | 'white';

export interface SpinnerProps extends Omit<React.SVGAttributes<SVGSVGElement>, 'color'> {
  size?: SpinnerSize;
  color?: SpinnerColor;
  label?: string;
}

const sizeMap: Record<SpinnerSize, string> = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-8 w-8',
};

const colorMap: Record<SpinnerColor, string> = {
  primary: 'text-brand-600',
  gray: 'text-gray-400',
  white: 'text-white',
};

const Spinner = React.forwardRef<SVGSVGElement, SpinnerProps>(
  ({ className, size = 'md', color = 'primary', label = 'Loading', ...props }, ref) => (
    <svg
      ref={ref}
      role="status"
      aria-label={label}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('animate-spin', sizeMap[size], colorMap[color], className)}
      {...props}
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        className="opacity-20"
      />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  )
);
Spinner.displayName = 'Spinner';

export { Spinner };
export type { SpinnerSize, SpinnerColor };
