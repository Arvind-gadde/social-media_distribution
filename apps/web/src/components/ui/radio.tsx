'use client';

import * as React from 'react';
import * as RadioGroupPrimitive from '@radix-ui/react-radio-group';
import { cn } from '@/lib/utils';

const RadioGroup = React.forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>
>(({ className, ...props }, ref) => (
  <RadioGroupPrimitive.Root
    ref={ref}
    className={cn('grid gap-2', className)}
    {...props}
  />
));
RadioGroup.displayName = 'RadioGroup';

export interface RadioItemProps
  extends React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  containerClassName?: string;
}

const RadioItem = React.forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive.Item>,
  RadioItemProps
>(
  (
    { className, containerClassName, id, label, description, ...props },
    ref
  ) => {
    const generatedId = React.useId();
    const radioId = id ?? generatedId;
    const hasLabel = Boolean(label || description);

    const control = (
      <RadioGroupPrimitive.Item
        ref={ref}
        id={radioId}
        className={cn(
          'peer aspect-square h-4 w-4 shrink-0 rounded-full border border-gray-300 bg-white shadow-xs',
          'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/24',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'data-[state=checked]:border-brand-600 data-[state=checked]:bg-brand-50',
          'dark:bg-gray-900 dark:border-gray-700 dark:data-[state=checked]:bg-brand-900/40',
          'transition-colors',
          className
        )}
        {...props}
      >
        <RadioGroupPrimitive.Indicator className="flex h-full w-full items-center justify-center after:block after:h-1.5 after:w-1.5 after:rounded-full after:bg-brand-600 dark:after:bg-brand-400" />
      </RadioGroupPrimitive.Item>
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
              htmlFor={radioId}
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
RadioItem.displayName = 'RadioItem';

const Radio = {
  Group: RadioGroup,
  Item: RadioItem,
};

export { RadioGroup, RadioItem, Radio };
