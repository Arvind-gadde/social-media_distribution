import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      aria-hidden
      className={cn('animate-pulse rounded-md bg-gray-200 dark:bg-gray-800', className)}
      {...props}
    />
  )
);
Skeleton.displayName = 'Skeleton';

// ─── SkeletonText ─────────────────────────────────────────────────────────

export interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  lines?: number;
  lineClassName?: string;
}

const SkeletonText = React.forwardRef<HTMLDivElement, SkeletonTextProps>(
  ({ className, lines = 3, lineClassName, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-3 w-full',
            // last line shorter for natural look
            i === lines - 1 && lines > 1 && 'w-3/5',
            lineClassName
          )}
        />
      ))}
    </div>
  )
);
SkeletonText.displayName = 'SkeletonText';

// ─── SkeletonAvatar ───────────────────────────────────────────────────────

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface SkeletonAvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: AvatarSize;
}

const avatarSizeMap: Record<AvatarSize, string> = {
  xs: 'h-6 w-6',
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
  xl: 'h-16 w-16',
};

const SkeletonAvatar = React.forwardRef<HTMLDivElement, SkeletonAvatarProps>(
  ({ className, size = 'md', ...props }, ref) => (
    <Skeleton
      ref={ref}
      className={cn('rounded-full', avatarSizeMap[size], className)}
      {...props}
    />
  )
);
SkeletonAvatar.displayName = 'SkeletonAvatar';

// ─── SkeletonCard ─────────────────────────────────────────────────────────

export interface SkeletonCardProps extends React.HTMLAttributes<HTMLDivElement> {
  showAvatar?: boolean;
  showImage?: boolean;
  lines?: number;
}

const SkeletonCard = React.forwardRef<HTMLDivElement, SkeletonCardProps>(
  ({ className, showAvatar = true, showImage = false, lines = 2, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4',
        className
      )}
      {...props}
    >
      {showImage && <Skeleton className="mb-4 h-40 w-full rounded-lg" />}
      <div className="flex items-center gap-3">
        {showAvatar && <SkeletonAvatar size="md" />}
        <div className="flex-1">
          <Skeleton className="h-3 w-2/5" />
          <Skeleton className="mt-2 h-2.5 w-1/4" />
        </div>
      </div>
      <div className="mt-4">
        <SkeletonText lines={lines} />
      </div>
    </div>
  )
);
SkeletonCard.displayName = 'SkeletonCard';

export { Skeleton, SkeletonText, SkeletonAvatar, SkeletonCard };
