'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string | boolean;
  maxLength?: number;
  showCounter?: boolean;
  autoGrow?: boolean;
  containerClassName?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      containerClassName,
      label,
      hint,
      error,
      maxLength,
      showCounter,
      autoGrow = false,
      id,
      disabled,
      value,
      defaultValue,
      onChange,
      rows = 3,
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const textareaId = id ?? generatedId;
    const hasError = Boolean(error);
    const errorMessage = typeof error === 'string' ? error : undefined;

    const innerRef = React.useRef<HTMLTextAreaElement | null>(null);
    React.useImperativeHandle(ref, () => innerRef.current as HTMLTextAreaElement);

    const [count, setCount] = React.useState<number>(() => {
      const initial = (value ?? defaultValue ?? '') as string;
      return typeof initial === 'string' ? initial.length : 0;
    });

    const adjustHeight = React.useCallback(() => {
      const el = innerRef.current;
      if (!el || !autoGrow) return;
      el.style.height = 'auto';
      el.style.height = `${el.scrollHeight}px`;
    }, [autoGrow]);

    React.useEffect(() => {
      if (autoGrow) adjustHeight();
    }, [autoGrow, adjustHeight, value]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setCount(e.target.value.length);
      if (autoGrow) adjustHeight();
      onChange?.(e);
    };

    const showCount = showCounter || typeof maxLength === 'number';
    const describedById =
      hint || errorMessage || showCount ? `${textareaId}-desc` : undefined;

    return (
      <div className={cn('flex w-full flex-col gap-1.5', containerClassName)}>
        {label && (
          <label
            htmlFor={textareaId}
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            {label}
          </label>
        )}
        <textarea
          ref={innerRef}
          id={textareaId}
          disabled={disabled}
          rows={rows}
          maxLength={maxLength}
          value={value}
          defaultValue={defaultValue}
          onChange={handleChange}
          aria-invalid={hasError || undefined}
          aria-describedby={describedById}
          className={cn(
            'w-full rounded-lg border bg-white px-3.5 py-2.5 text-base text-gray-900 placeholder:text-gray-500',
            'shadow-xs transition-colors',
            'focus:outline-none focus:ring-4',
            'disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500',
            'dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500',
            'dark:disabled:bg-gray-800 dark:disabled:text-gray-500',
            autoGrow ? 'resize-none overflow-hidden' : 'resize-y',
            hasError
              ? 'border-error-500 focus:border-error-500 focus:ring-error-100 dark:border-error-500 dark:focus:ring-error-900/40'
              : 'border-gray-300 focus:border-brand-500 focus:ring-brand-100 dark:border-gray-700 dark:focus:border-brand-500 dark:focus:ring-brand-900/40',
            className
          )}
          {...props}
        />
        {(errorMessage || hint || showCount) && (
          <div
            id={describedById}
            className="flex items-start justify-between gap-2 text-sm"
          >
            <p
              className={cn(
                errorMessage
                  ? 'text-error-600 dark:text-error-400'
                  : 'text-gray-500 dark:text-gray-400'
              )}
            >
              {errorMessage ?? hint ?? ''}
            </p>
            {showCount && (
              <span className="shrink-0 text-gray-500 tabular-nums dark:text-gray-400">
                {count}
                {typeof maxLength === 'number' ? ` / ${maxLength}` : ''}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };
