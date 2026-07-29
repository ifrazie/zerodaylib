/**
 * SectionHeader — uppercase muted section label with optional count and actions.
 *
 * Used inside the sidebar to label navigation groups, and on list pages as
 * secondary headers below the page title.
 */

import type { ReactNode } from 'react';

export interface SectionHeaderProps {
  title: string;
  /** Optional count rendered as a small mono badge next to the title. */
  count?: number;
  /** Optional right-side actions (e.g., filter buttons). */
  actions?: ReactNode;
  className?: string;
}

export function SectionHeader({
  title,
  count,
  actions,
  className = '',
}: SectionHeaderProps) {
  return (
    <div className={`flex items-center justify-between mb-3 ${className}`}>
      <div className="flex items-center gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)]">
          {title}
        </h3>
        {typeof count === 'number' ? (
          <span className="font-mono text-[11px] text-[var(--color-fg-subtle)]">
            {count}
          </span>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
