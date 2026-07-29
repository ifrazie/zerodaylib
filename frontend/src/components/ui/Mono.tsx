/**
 * Mono — wraps children in JetBrains Mono with tabular numbers.
 *
 * Use for anything that must line up: identifiers, CVE IDs, UUIDs, hashes,
 * timestamps, JSON keys, IP addresses, port numbers, similarity scores.
 * Signals to the reader "this is data" as opposed to prose.
 */

import type { ReactNode } from 'react';

export interface MonoProps {
  children: ReactNode;
  size?: 'xs' | 'sm' | 'base';
  /** Optional semantic color; defaults to inherit from parent. */
  tone?: 'default' | 'muted' | 'subtle' | 'accent';
  className?: string;
}

const SIZE_CLASS: Record<NonNullable<MonoProps['size']>, string> = {
  xs: 'text-xs',
  sm: 'text-sm',
  base: 'text-base',
};

const TONE_STYLE: Record<NonNullable<MonoProps['tone']>, React.CSSProperties> = {
  default: {},
  muted:   { color: 'var(--color-fg-muted)' },
  subtle:  { color: 'var(--color-fg-subtle)' },
  accent:  { color: 'var(--color-accent-fg)' },
};

export function Mono({
  children,
  size = 'sm',
  tone = 'default',
  className = '',
}: MonoProps) {
  return (
    <span
      className={`font-mono ${SIZE_CLASS[size]} ${className}`}
      style={TONE_STYLE[tone]}
    >
      {children}
    </span>
  );
}
