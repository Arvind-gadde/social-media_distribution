'use client';

import * as React from 'react';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { cn } from '@/lib/utils';

export type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
export type AvatarStatus = 'online' | 'offline' | 'busy' | 'away';

const sizeStyles: Record<AvatarSize, string> = {
  xs: 'h-6 w-6 text-xs',
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-14 w-14 text-base',
  '2xl': 'h-16 w-16 text-lg',
};

const statusSizeStyles: Record<AvatarSize, string> = {
  xs: 'h-1.5 w-1.5 ring-1',
  sm: 'h-2 w-2 ring-2',
  md: 'h-2.5 w-2.5 ring-2',
  lg: 'h-3 w-3 ring-2',
  xl: 'h-3.5 w-3.5 ring-2',
  '2xl': 'h-4 w-4 ring-2',
};

const statusColorStyles: Record<AvatarStatus, string> = {
  online: 'bg-success-500',
  offline: 'bg-gray-400',
  busy: 'bg-error-500',
  away: 'bg-warning-500',
};

export interface AvatarProps
  extends React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root> {
  size?: AvatarSize;
  status?: AvatarStatus;
  src?: string;
  alt?: string;
  fallback?: React.ReactNode;
  imgProps?: React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>;
}

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  AvatarProps
>(
  (
    { className, size = 'md', status, src, alt, fallback, imgProps, children, ...props },
    ref
  ) => {
    return (
      <AvatarPrimitive.Root
        ref={ref}
        className={cn(
          'relative inline-flex shrink-0 overflow-visible',
          className
        )}
        {...props}
      >
        <span
          className={cn(
            'flex h-full w-full items-center justify-center overflow-hidden rounded-full bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
            sizeStyles[size]
          )}
        >
          {src && (
            <AvatarPrimitive.Image
              src={src}
              alt={alt ?? ''}
              className="aspect-square h-full w-full object-cover"
              {...imgProps}
            />
          )}
          <AvatarPrimitive.Fallback
            delayMs={src ? 400 : 0}
            className="flex h-full w-full items-center justify-center font-medium uppercase"
          >
            {fallback ?? children}
          </AvatarPrimitive.Fallback>
        </span>
        {status && (
          <span
            className={cn(
              'absolute bottom-0 right-0 block rounded-full ring-white dark:ring-gray-900',
              statusSizeStyles[size],
              statusColorStyles[status]
            )}
            aria-label={status}
          />
        )}
      </AvatarPrimitive.Root>
    );
  }
);
Avatar.displayName = 'Avatar';

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square h-full w-full object-cover', className)}
    {...props}
  />
));
AvatarImage.displayName = 'AvatarImage';

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-gray-100 font-medium uppercase text-gray-700 dark:bg-gray-800 dark:text-gray-200',
      className
    )}
    {...props}
  />
));
AvatarFallback.displayName = 'AvatarFallback';

export interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: AvatarSize;
  max?: number;
  total?: number;
  spacing?: 'tight' | 'normal';
}

const groupOverlap: Record<AvatarSize, Record<'tight' | 'normal', string>> = {
  xs: { tight: '-space-x-1.5', normal: '-space-x-1' },
  sm: { tight: '-space-x-2', normal: '-space-x-1.5' },
  md: { tight: '-space-x-2.5', normal: '-space-x-2' },
  lg: { tight: '-space-x-3', normal: '-space-x-2' },
  xl: { tight: '-space-x-3.5', normal: '-space-x-2.5' },
  '2xl': { tight: '-space-x-4', normal: '-space-x-3' },
};

const AvatarGroup = React.forwardRef<HTMLDivElement, AvatarGroupProps>(
  (
    {
      className,
      size = 'md',
      max = 4,
      total,
      spacing = 'normal',
      children,
      ...props
    },
    ref
  ) => {
    const childArray = React.Children.toArray(children).filter(
      React.isValidElement
    ) as React.ReactElement<AvatarProps>[];
    const visible = childArray.slice(0, max);
    const totalCount = total ?? childArray.length;
    const overflow = totalCount - visible.length;

    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center',
          groupOverlap[size][spacing],
          className
        )}
        {...props}
      >
        {visible.map((child, idx) =>
          React.cloneElement(child, {
            key: child.key ?? idx,
            size: child.props.size ?? size,
            className: cn(
              'ring-2 ring-white dark:ring-gray-900',
              child.props.className
            ),
          })
        )}
        {overflow > 0 && (
          <span
            className={cn(
              'inline-flex items-center justify-center rounded-full bg-gray-100 font-medium text-gray-700 ring-2 ring-white dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-900',
              sizeStyles[size]
            )}
          >
            +{overflow}
          </span>
        )}
      </div>
    );
  }
);
AvatarGroup.displayName = 'AvatarGroup';

export { Avatar, AvatarImage, AvatarFallback, AvatarGroup };
