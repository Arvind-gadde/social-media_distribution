'use client';

import * as React from 'react';
import * as SwitchPrimitive from '@radix-ui/react-switch';
import { cn } from '@/lib/utils';

export type SwitchSize = 'sm' | 'md';

export interface SwitchProps
  extends React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  switchSize?: SwitchSize;
  containerClassName?: string;
}

const trackSizes: Record<SwitchSize, string> = {
  sm: 'h-5 w-9',
  md: 'h-6 w-11',
};

const thumbSizes: Record<SwitchSize, string> = {
  sm: 'h-4 w-4 data-[state=checked]:translate-x-4',
  md: 'h-5 w-5 data-[state=checked]:translate-x-5',
};

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  SwitchProps
>(
  (
    {
      className,
      containerClassName,
      id,
      label,
      description,
      switchSize = 'md',
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const switchId = id ?? generatedId;
    const hasLabel = Boolean(label || description);

    const control = (
      <SwitchPrimitive.Root
        ref={ref}
        id={switchId}
        className={cn(
          'peer inline-flex shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors',
          'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/24',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'data-[state=checked]:bg-brand-600 data-[state=unchecked]:bg-gray-200',
          'dark:data-[state=unchecked]:bg-gray-700',
          trackSizes[switchSize],
          className
        )}
        {...props}
      >
        <SwitchPrimitive.Thumb
          className={cn(
            'pointer-events-none block rounded-full bg-white shadow-sm ring-0 transition-transform data-[state=unchecked]:translate-x-0.5',
            thumbSizes[switchSize]
          )}
        />
      </SwitchPrimitive.Root>
    );

    if (!hasLabel) return control;

    return (
      <div className={cn('flex items-start gap-3', containerClassName)}>
        {control}
        <div className="grid gap-0.5 leading-none">
          {label && (
            <label
              htmlFor={switchId}
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
  }
);

Switch.displayName = 'Switch';

export { Switch };
