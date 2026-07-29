/**
 * DataTable — dense, hoverable, dark-theme table for list pages.
 *
 * Design choices:
 *   - 12px vertical padding (dense, security-console feel)
 *   - Sticky header
 *   - Subtle hover-row (bg-inset)
 *   - Optional zebra striping
 *   - No cell borders; horizontal dividers only via border-b
 *   - Empty state renders in the tbody area
 *
 * Typing: columns are generic over the row type so consumers get full
 * type safety on the accessor function.
 */

import type { ReactNode } from 'react';

export interface Column<T> {
  /** Unique key per column (used for React keys and as a fallback header). */
  key: string;
  /** Header label. */
  header: ReactNode;
  /** Function to extract/render the cell value for a given row. */
  cell: (row: T) => ReactNode;
  /** Optional per-column CSS class applied to <td>. */
  className?: string;
  /** Right-align numeric columns for readability. */
  align?: 'left' | 'right';
  /** Fixed width (any valid CSS width). */
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  /** Function to compute a stable React key per row. */
  rowKey: (row: T, index: number) => string;
  /** Optional onClick handler that receives the row. */
  onRowClick?: (row: T) => void;
  /** Node rendered when rows.length === 0. */
  emptyState?: ReactNode;
  /** Zebra-stripe alternate rows. Off by default. */
  zebra?: boolean;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  emptyState,
  zebra = false,
  className = '',
}: DataTableProps<T>) {
  const isEmpty = rows.length === 0;

  return (
    <div
      className={`rounded-md border overflow-hidden ${className}`}
      style={{
        borderColor: 'var(--color-border-default)',
        background: 'var(--color-bg-subtle)',
      }}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead
            style={{
              background: 'var(--color-bg-default)',
              borderBottom: '1px solid var(--color-border-default)',
            }}
          >
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)] ${
                    col.align === 'right' ? 'text-right' : 'text-left'
                  }`}
                  style={col.width ? { width: col.width } : undefined}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isEmpty ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-sm text-[var(--color-fg-muted)]"
                >
                  {emptyState ?? 'No data available.'}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => {
                const stripe =
                  zebra && index % 2 === 1
                    ? { background: 'rgba(240, 246, 252, 0.02)' }
                    : undefined;
                return (
                  <tr
                    key={rowKey(row, index)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={`border-b transition-colors ${
                      onRowClick ? 'cursor-pointer' : ''
                    } hover:bg-[var(--color-bg-inset)]`}
                    style={{
                      borderColor: 'var(--color-border-muted)',
                      ...stripe,
                    }}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`px-4 py-3 whitespace-nowrap text-[var(--color-fg-default)] ${
                          col.align === 'right' ? 'text-right' : 'text-left'
                        } ${col.className ?? ''}`}
                      >
                        {col.cell(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
