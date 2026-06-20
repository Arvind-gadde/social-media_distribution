'use client';

import * as React from 'react';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import { Check, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CheckboxProps
  extends React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  containerClassName?: string;
}

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  CheckboxProps
>(({ className, containerClassName, id, label, description, ...props }, ref) => {
  const generatedId = React.useId();
  const checkboxId = id ?? generatedId;
  const hasLabel = Boolean(label || description);

  const control = (
    <CheckboxPrimitive.Root
      ref={ref}
      id={checkboxId}
      className={cn(
        'peer h-4 w-4 shrink-0 rounded border border-gray-300 bg-white shadow-xs',
        'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/24',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'data-[state=checked]:border-brand-600 data-[state=checked]:bg-brand-600 data-[state=checked]:text-white',
        'data-[state=indeterminate]:border-brand-600 data-[state=indeterminate]:bg-brand-600 data-[state=indeterminate]:text-white',
        'dark:bg-gray-900 dark:border-gray-700',
        'transition-colors',
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center text-current">
        {props.checked === 'indeterminate' ? (
          <Minus className="h-3 w-3" strokeWidth={3} />
        ) : (
          <Check className="h-3 w-3" strokeWidth={3} />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );

  if (!hasLabel) {
    return control;
  }

  return (
    <div className={cn('flex items-start gap-2', containerClassName)}>
      {control}
      <div className="grid gap-0.5 leading-none">
        {label && (
          <label
            htmlFor={checkboxId}
            className="text-sm font-medium text-gray-700 dark:text-gray-200 peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {label}
          </label>
        )}
        {description && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        )}
      </div>
    </div>
  );
});

Checkbox.displayName = 'Checkbox';

export { Checkbox };
