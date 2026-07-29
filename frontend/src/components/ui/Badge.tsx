/**
 * Badge — outlined semantic badge for severity, governance state, and neutral tags.
 *
 * Variants map 1:1 to design tokens defined in globals.css. Do NOT add
 * decorative variants; every badge must communicate meaning.
 *
 * Severity variants (from data): critical | high | medium | low
 * Governance variants:            allow | deny | manual_review | under_review | unreviewed | approved | rejected
 * Neutral:                        neutral (labels, environments, tags)
 */

import type { ReactNode } from 'react';

export type BadgeVariant =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'allow'
  | 'deny'
  | 'manual_review'
  | 'under_review'
  | 'unreviewed'
  | 'approved'
  | 'rejected'
  | 'neutral';

export interface BadgeProps {
  variant: BadgeVariant;
  /** Optional label override. If omitted, uses the variant name (upper-cased, underscores → spaces). */
  children?: ReactNode;
  /** Solid fill instead of subtle background. Use sparingly (e.g., top-of-page status). */
  emphasis?: boolean;
  /** Extra classes for layout adjustments only. */
  className?: string;
}

type BadgeTheme = {
  fg: string;
  bg: string;
  border: string;
  emphasisBg: string;
  emphasisFg: string;
};

const THEMES: Record<BadgeVariant, BadgeTheme> = {
  critical: {
    fg: 'var(--color-danger-fg)',
    bg: 'var(--color-danger-subtle)',
    border: 'var(--color-danger-muted)',
    emphasisBg: 'var(--color-danger-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  high: {
    fg: 'var(--color-severe-fg)',
    bg: 'var(--color-severe-subtle)',
    border: 'var(--color-severe-muted)',
    emphasisBg: 'var(--color-severe-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  medium: {
    fg: 'var(--color-attention-fg)',
    bg: 'var(--color-attention-subtle)',
    border: 'var(--color-attention-muted)',
    emphasisBg: 'var(--color-attention-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  low: {
    fg: 'var(--color-success-fg)',
    bg: 'var(--color-success-subtle)',
    border: 'var(--color-success-muted)',
    emphasisBg: 'var(--color-success-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  allow: {
    fg: 'var(--color-success-fg)',
    bg: 'var(--color-success-subtle)',
    border: 'var(--color-success-muted)',
    emphasisBg: 'var(--color-success-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  approved: {
    fg: 'var(--color-success-fg)',
    bg: 'var(--color-success-subtle)',
    border: 'var(--color-success-muted)',
    emphasisBg: 'var(--color-success-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  deny: {
    fg: 'var(--color-danger-fg)',
    bg: 'var(--color-danger-subtle)',
    border: 'var(--color-danger-muted)',
    emphasisBg: 'var(--color-danger-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  rejected: {
    fg: 'var(--color-danger-fg)',
    bg: 'var(--color-danger-subtle)',
    border: 'var(--color-danger-muted)',
    emphasisBg: 'var(--color-danger-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  manual_review: {
    fg: 'var(--color-done-fg)',
    bg: 'var(--color-done-subtle)',
    border: 'var(--color-done-muted)',
    emphasisBg: 'var(--color-done-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  under_review: {
    fg: 'var(--color-done-fg)',
    bg: 'var(--color-done-subtle)',
    border: 'var(--color-done-muted)',
    emphasisBg: 'var(--color-done-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  unreviewed: {
    fg: 'var(--color-attention-fg)',
    bg: 'var(--color-attention-subtle)',
    border: 'var(--color-attention-muted)',
    emphasisBg: 'var(--color-attention-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
  neutral: {
    fg: 'var(--color-fg-muted)',
    bg: 'var(--color-neutral-subtle)',
    border: 'var(--color-border-default)',
    emphasisBg: 'var(--color-neutral-emphasis)',
    emphasisFg: 'var(--color-fg-on-emphasis)',
  },
};

function defaultLabel(variant: BadgeVariant): string {
  return variant.replace(/_/g, ' ').toUpperCase();
}

export function Badge({
  variant,
  children,
  emphasis = false,
  className = '',
}: BadgeProps) {
  const theme = THEMES[variant];
  const style: React.CSSProperties = emphasis
    ? { color: theme.emphasisFg, background: theme.emphasisBg, borderColor: theme.emphasisBg }
    : { color: theme.fg, background: theme.bg, borderColor: theme.border };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium font-mono border tracking-wide ${className}`}
      style={style}
    >
      {children ?? defaultLabel(variant)}
    </span>
  );
}
