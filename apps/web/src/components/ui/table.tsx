'use client';

import * as React from 'react';
import {
  type ColumnDef,
  type Row,
  type Table as ReactTable,
  type SortingState,
  type RowSelectionState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronsUpDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Primitive table elements ─────────────────────────────────────────────

const TableRoot = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table
        ref={ref}
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
);
TableRoot.displayName = 'Table';

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      'sticky top-0 z-10 bg-gray-50 dark:bg-gray-900',
      'border-b border-gray-200 dark:border-gray-800',
      className
    )}
    {...props}
  />
));
TableHeader.displayName = 'TableHeader';

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props} />
));
TableBody.displayName = 'TableBody';

interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  selected?: boolean;
}

const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, selected, ...props }, ref) => (
    <tr
      ref={ref}
      data-state={selected ? 'selected' : undefined}
      className={cn(
        'border-b border-gray-200 dark:border-gray-800 transition-colors',
        'hover:bg-gray-50 dark:hover:bg-gray-900',
        selected && 'bg-brand-50 dark:bg-brand-950 hover:bg-brand-50 dark:hover:bg-brand-950',
        className
      )}
      {...props}
    />
  )
);
TableRow.displayName = 'TableRow';

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    scope="col"
    className={cn(
      'h-11 px-4 text-left align-middle',
      'text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400',
      className
    )}
    {...props}
  />
));
TableHead.displayName = 'TableHead';

interface TableCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
  density?: TableDensity;
}

const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, density = 'comfortable', ...props }, ref) => (
    <td
      ref={ref}
      className={cn(
        'px-4 align-middle text-sm text-gray-700 dark:text-gray-300',
        density === 'compact' && 'py-2',
        density === 'comfortable' && 'py-3',
        density === 'relaxed' && 'py-4',
        className
      )}
      {...props}
    />
  )
);
TableCell.displayName = 'TableCell';

// ─── TanStack wrapper ──────────────────────────────────────────────────────

type TableDensity = 'compact' | 'comfortable' | 'relaxed';

interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  enableSorting?: boolean;
  enableRowSelection?: boolean;
  density?: TableDensity;
  pageSize?: number;
  /** Pass a stable function. Receives row.original. */
  onRowClick?: (row: TData) => void;
  className?: string;
  /** Returns the underlying tanstack table instance for advanced control. */
  tableRef?: React.MutableRefObject<ReactTable<TData> | null>;
  emptyState?: React.ReactNode;
}

function DataTable<TData>({
  data,
  columns,
  enableSorting = true,
  enableRowSelection = false,
  density = 'comfortable',
  pageSize = 10,
  onRowClick,
  className,
  tableRef,
  emptyState,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({});

  const table = useReactTable({
    data,
    columns,
    state: { sorting, rowSelection },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    enableSorting,
    enableRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize },
    },
  });

  React.useEffect(() => {
    if (tableRef) {
      tableRef.current = table;
    }
  }, [table, tableRef]);

  return (
    <TableRoot className={className}>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <tr key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              const canSort = header.column.getCanSort();
              const sorted = header.column.getIsSorted();
              return (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : canSort ? (
                    <button
                      type="button"
                      onClick={header.column.getToggleSortingHandler()}
                      className="inline-flex items-center gap-1 hover:text-gray-900 dark:hover:text-gray-100"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sorted === 'asc' ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : sorted === 'desc' ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronsUpDown className="h-3 w-3 opacity-50" />
                      )}
                    </button>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </TableHead>
              );
            })}
          </tr>
        ))}
      </TableHeader>

      <TableBody>
        {table.getRowModel().rows.length === 0 ? (
          <tr>
            <td
              colSpan={columns.length}
              className="px-4 py-10 text-center text-sm text-gray-500 dark:text-gray-400"
            >
              {emptyState ?? 'No results.'}
            </td>
          </tr>
        ) : (
          table.getRowModel().rows.map((row: Row<TData>) => (
            <TableRow
              key={row.id}
              selected={row.getIsSelected()}
              onClick={onRowClick ? () => onRowClick(row.original) : undefined}
              className={onRowClick ? 'cursor-pointer' : undefined}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id} density={density}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </TableRoot>
  );
}

// ─── Pagination control ────────────────────────────────────────────────────

interface TablePaginationProps<TData> {
  table: ReactTable<TData>;
  className?: string;
  pageSizeOptions?: number[];
}

function TablePagination<TData>({
  table,
  className,
  pageSizeOptions = [10, 25, 50, 100],
}: TablePaginationProps<TData>) {
  const pageIndex = table.getState().pagination.pageIndex;
  const pageSize = table.getState().pagination.pageSize;
  const pageCount = table.getPageCount();
  const total = table.getFilteredRowModel().rows.length;
  const start = total === 0 ? 0 : pageIndex * pageSize + 1;
  const end = Math.min((pageIndex + 1) * pageSize, total);

  return (
    <div
      className={cn(
        'flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between',
        'border-t border-gray-200 dark:border-gray-800 px-4 py-3',
        className
      )}
    >
      <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
        <span>
          {start}-{end} of {total}
        </span>
        <label className="flex items-center gap-2">
          <span>Rows per page</span>
          <select
            value={pageSize}
            onChange={(e) => table.setPageSize(Number(e.target.value))}
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
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
          className={cn(
            'inline-flex h-8 items-center gap-1 rounded-md border border-gray-300 dark:border-gray-700',
            'bg-white dark:bg-gray-900 px-2.5 text-sm font-medium text-gray-700 dark:text-gray-300',
            'hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:pointer-events-none'
          )}
        >
          <ChevronLeft className="h-4 w-4" /> Previous
        </button>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          Page {pageIndex + 1} of {Math.max(pageCount, 1)}
        </span>
        <button
          type="button"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
          className={cn(
            'inline-flex h-8 items-center gap-1 rounded-md border border-gray-300 dark:border-gray-700',
            'bg-white dark:bg-gray-900 px-2.5 text-sm font-medium text-gray-700 dark:text-gray-300',
            'hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:pointer-events-none'
          )}
        >
          Next <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ─── Density toggle ────────────────────────────────────────────────────────

interface TableDensityToggleProps {
  value: TableDensity;
  onChange: (value: TableDensity) => void;
  className?: string;
}

function TableDensityToggle({ value, onChange, className }: TableDensityToggleProps) {
  const options: Array<{ value: TableDensity; label: string }> = [
    { value: 'compact', label: 'Compact' },
    { value: 'comfortable', label: 'Default' },
    { value: 'relaxed', label: 'Relaxed' },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Row density"
      className={cn(
        'inline-flex items-center rounded-lg border border-gray-200 dark:border-gray-800',
        'bg-white dark:bg-gray-950 p-1',
        className
      )}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={value === opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            'h-7 rounded-md px-2.5 text-xs font-medium transition-colors',
            value === opt.value
              ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export {
  TableRoot as Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  DataTable,
  TablePagination,
  TableDensityToggle,
};
export type {
  TableDensity,
  TableRowProps,
  TableCellProps,
  DataTableProps,
  TablePaginationProps,
  TableDensityToggleProps,
};
