'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export type InputSize = 'sm' | 'md' | 'lg';

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  hint?: string;
  error?: string | boolean;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
  inputSize?: InputSize;
  containerClassName?: string;
}

const sizeStyles: Record<InputSize, string> = {
  sm: 'h-9 text-sm',
  md: 'h-10 text-base',
  lg: 'h-11 text-base',
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      containerClassName,
      label,
      hint,
      error,
      leadingIcon,
      trailingIcon,
      inputSize = 'md',
      id,
      disabled,
      type = 'text',
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;
    const hasError = Boolean(error);
    const errorMessage = typeof error === 'string' ? error : undefined;
    const describedById = hint || errorMessage ? `${inputId}-desc` : undefined;

    return (
      <div className={cn('flex w-full flex-col gap-1.5', containerClassName)}>
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leadingIcon && (
            <span
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 [&_svg]:h-4 [&_svg]:w-4"
              aria-hidden="true"
            >
              {leadingIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            type={type}
            disabled={disabled}
            aria-invalid={hasError || undefined}
            aria-describedby={describedById}
            className={cn(
              'w-full rounded-lg border bg-white px-3.5 text-gray-900 placeholder:text-gray-500',
              'shadow-xs transition-colors',
              'focus:outline-none focus:ring-4',
              'disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500',
              'dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500',
              'dark:disabled:bg-gray-800 dark:disabled:text-gray-500',
              sizeStyles[inputSize],
              leadingIcon && 'pl-10',
              trailingIcon && 'pr-10',
              hasError
                ? 'border-error-500 focus:border-error-500 focus:ring-error-100 dark:border-error-500 dark:focus:ring-error-900/40'
                : 'border-gray-300 focus:border-brand-500 focus:ring-brand-100 dark:border-gray-700 dark:focus:border-brand-500 dark:focus:ring-brand-900/40',
              className
            )}
            {...props}
          />
          {trailingIcon && (
            <span
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 [&_svg]:h-4 [&_svg]:w-4"
              aria-hidden="true"
            >
              {trailingIcon}
            </span>
          )}
        </div>
        {(errorMessage || hint) && (
          <p
            id={describedById}
            className={cn(
              'text-sm',
              errorMessage
                ? 'text-error-600 dark:text-error-400'
                : 'text-gray-500 dark:text-gray-400'
            )}
          >
            {errorMessage ?? hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
