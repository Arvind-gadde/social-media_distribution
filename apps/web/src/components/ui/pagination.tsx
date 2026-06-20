'use client';

import * as React from 'react';
import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Build an Untitled-UI-style pagination range:
 *   1 2 3 ... 10
 * Always shows first + last; current page surrounded by `siblings` pages.
 */
function getPaginationRange(currentPage: number, pageCount: number, siblings = 1): (number | 'ellipsis')[] {
  if (pageCount <= 1) return [1].slice(0, pageCount);
  const totalNumbers = siblings * 2 + 5; // first, last, current, 2 ellipses, siblings
  if (pageCount <= totalNumbers) {
    return Array.from({ length: pageCount }, (_, i) => i + 1);
  }

  const leftSibling = Math.max(currentPage - siblings, 1);
  const rightSibling = Math.min(currentPage + siblings, pageCount);

  const showLeftEllipsis = leftSibling > 2;
  const showRightEllipsis = rightSibling < pageCount - 1;

  const range: (number | 'ellipsis')[] = [];
  range.push(1);
  if (showLeftEllipsis) range.push('ellipsis');
  for (let p = leftSibling; p <= rightSibling; p++) {
    if (p !== 1 && p !== pageCount) range.push(p);
  }
  if (showRightEllipsis) range.push('ellipsis');
  range.push(pageCount);
  return range;
}

// ─── Building blocks ──────────────────────────────────────────────────────

const Pagination = ({ className, ...props }: React.ComponentPropsWithoutRef<'nav'>) => (
  <nav
    role="navigation"
    aria-label="pagination"
    className={cn('flex w-full items-center justify-between gap-4', className)}
    {...props}
  />
);
Pagination.displayName = 'Pagination';

const PaginationContent = React.forwardRef<HTMLUListElement, React.ComponentPropsWithoutRef<'ul'>>(
  ({ className, ...props }, ref) => (
    <ul ref={ref} className={cn('flex items-center gap-1', className)} {...props} />
  )
);
PaginationContent.displayName = 'PaginationContent';

const PaginationItem = React.forwardRef<HTMLLIElement, React.ComponentPropsWithoutRef<'li'>>(
  ({ className, ...props }, ref) => <li ref={ref} className={cn('', className)} {...props} />
);
PaginationItem.displayName = 'PaginationItem';

interface PaginationLinkProps extends React.ComponentPropsWithoutRef<'button'> {
  isActive?: boolean;
}

const PaginationLink = React.forwardRef<HTMLButtonElement, PaginationLinkProps>(
  ({ className, isActive, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'inline-flex h-9 min-w-9 items-center justify-center rounded-md px-3 text-sm font-medium',
        'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        'disabled:pointer-events-none disabled:opacity-50',
        isActive
          ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 hover:text-gray-900 dark:hover:text-gray-100',
        className
      )}
      {...props}
    />
  )
);
PaginationLink.displayName = 'PaginationLink';

const PaginationPrevious = ({ className, ...props }: PaginationLinkProps) => (
  <PaginationLink
    aria-label="Go to previous page"
    className={cn('gap-1 pl-2', className)}
    {...props}
  >
    <ChevronLeft className="h-4 w-4" />
    <span>Previous</span>
  </PaginationLink>
);
PaginationPrevious.displayName = 'PaginationPrevious';

const PaginationNext = ({ className, ...props }: PaginationLinkProps) => (
  <PaginationLink aria-label="Go to next page" className={cn('gap-1 pr-2', className)} {...props}>
    <span>Next</span>
    <ChevronRight className="h-4 w-4" />
  </PaginationLink>
);
PaginationNext.displayName = 'PaginationNext';

const PaginationEllipsis = ({ className, ...props }: React.ComponentPropsWithoutRef<'span'>) => (
  <span
    aria-hidden
    className={cn('flex h-9 w-9 items-center justify-center text-gray-400', className)}
    {...props}
  >
    <MoreHorizontal className="h-4 w-4" />
    <span className="sr-only">More pages</span>
  </span>
);
PaginationEllipsis.displayName = 'PaginationEllipsis';

// ─── Composite pagination ──────────────────────────────────────────────────

export interface PaginationControlProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  totalItems?: number;
  showJumpTo?: boolean;
  siblings?: number;
  className?: string;
}

const PaginationControl = ({
  page,
  pageCount,
  onPageChange,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  totalItems,
  showJumpTo = false,
  siblings = 1,
  className,
}: PaginationControlProps) => {
  const safePageCount = Math.max(pageCount, 1);
  const range = getPaginationRange(page, safePageCount, siblings);
  const [jumpValue, setJumpValue] = React.useState('');

  const handleJump = (e: React.FormEvent) => {
    e.preventDefault();
    const target = Number(jumpValue);
    if (!Number.isFinite(target)) return;
    const clamped = Math.min(Math.max(1, Math.floor(target)), safePageCount);
    onPageChange(clamped);
    setJumpValue('');
  };

  return (
    <Pagination className={className}>
      <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
        {typeof totalItems === 'number' && pageSize ? (
          <span>
            {totalItems === 0
              ? '0 results'
              : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, totalItems)} of ${totalItems}`}
          </span>
        ) : (
          <span>
            Page {page} of {safePageCount}
          </span>
        )}
        {pageSize !== undefined && onPageSizeChange && (
          <label className="flex items-center gap-2">
            <span>Show</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className={cn(
                'h-8 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900',
                'px-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500'
              )}
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
          />
        </PaginationItem>
        {range.map((entry, idx) =>
          entry === 'ellipsis' ? (
            <PaginationItem key={`e-${idx}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={entry}>
              <PaginationLink isActive={entry === page} onClick={() => onPageChange(entry)}>
                {entry}
              </PaginationLink>
            </PaginationItem>
          )
        )}
        <PaginationItem>
          <PaginationNext
            onClick={() => onPageChange(Math.min(safePageCount, page + 1))}
            disabled={page >= safePageCount}
          />
        </PaginationItem>
      </PaginationContent>

      {showJumpTo && (
        <form onSubmit={handleJump} className="flex items-center gap-2 text-sm">
          <label htmlFor="jump-to-page" className="text-gray-600 dark:text-gray-400">
            Go to
          </label>
          <input
            id="jump-to-page"
            type="number"
            min={1}
            max={safePageCount}
            value={jumpValue}
            onChange={(e) => setJumpValue(e.target.value)}
            className={cn(
              'h-8 w-16 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900',
              'px-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500'
            )}
          />
        </form>
      )}
    </Pagination>
  );
};
PaginationControl.displayName = 'PaginationControl';

export {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationPrevious,
  PaginationNext,
  PaginationEllipsis,
  PaginationControl,
  getPaginationRange,
};
export type { PaginationLinkProps };
