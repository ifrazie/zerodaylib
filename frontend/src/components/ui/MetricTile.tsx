/**
 * MetricTile — compact number-forward summary card.
 *
 * Used at the top of every list page to surface headline numbers.
 * No sparklines, no charts — just the number and its context.
 */

import type { ReactNode } from 'react';

export type MetricTone = 'default' | 'critical' | 'success' | 'attention' | 'accent';

export interface MetricTileProps {
  label: string;
  value: string | number;
  sublabel?: string;
  tone?: MetricTone;
  /** Optional trailing icon or accessory (e.g., a small badge). */
  accessory?: ReactNode;
  className?: string;
}

const TONE_COLOR: Record<MetricTone, string> = {
  default:   'var(--color-fg-default)',
  critical:  'var(--color-danger-fg)',
  success:   'var(--color-success-fg)',
  attention: 'var(--color-attention-fg)',
  accent:    'var(--color-accent-fg)',
};

export function MetricTile({
  label,
  value,
  sublabel,
  tone = 'default',
  accessory,
  className = '',
}: MetricTileProps) {
  return (
    <div
      className={`rounded-md border p-4 min-w-[160px] ${className}`}
      style={{
        borderColor: 'var(--color-border-default)',
        background: 'var(--color-bg-subtle)',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)]">
          {label}
        </div>
        {accessory ? <div className="shrink-0">{accessory}</div> : null}
      </div>
      <div
        className="mt-1 font-mono text-2xl leading-none tabular-nums"
        style={{ color: TONE_COLOR[tone] }}
      >
        {value}
      </div>
      {sublabel ? (
        <div className="mt-1 text-xs text-[var(--color-fg-subtle)]">{sublabel}</div>
      ) : null}
    </div>
  );
}
