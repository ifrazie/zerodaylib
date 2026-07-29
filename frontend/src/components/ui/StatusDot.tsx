/**
 * StatusDot — small colored dot with an optional label for system-health rows.
 *
 * Statuses map to semantic tokens:
 *   healthy   → success-fg (green)
 *   degraded  → attention-fg (yellow)
 *   unhealthy → danger-fg (red)
 *   unknown   → fg-subtle (grey)
 *
 * Adds a subtle glow via box-shadow so the dot reads as a "signal light."
 */

export type Status = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

export interface StatusDotProps {
  status: Status;
  label?: string;
  /** Optional right-side value (e.g., "3 nodes"). Rendered in mono. */
  detail?: string;
  className?: string;
}

const STATUS_COLOR: Record<Status, string> = {
  healthy:   'var(--color-success-fg)',
  degraded:  'var(--color-attention-fg)',
  unhealthy: 'var(--color-danger-fg)',
  unknown:   'var(--color-fg-subtle)',
};

export function StatusDot({
  status,
  label,
  detail,
  className = '',
}: StatusDotProps) {
  const color = STATUS_COLOR[status];
  return (
    <div className={`inline-flex items-center gap-2 text-sm ${className}`}>
      <span
        className="inline-block h-2 w-2 rounded-full shrink-0"
        style={{
          background: color,
          boxShadow: status === 'unknown' ? 'none' : `0 0 6px ${color}`,
        }}
        aria-label={status}
      />
      {label ? (
        <span className="text-[var(--color-fg-default)]">{label}</span>
      ) : null}
      {detail ? (
        <span className="font-mono text-xs text-[var(--color-fg-muted)] ml-auto">
          {detail}
        </span>
      ) : null}
    </div>
  );
}
