"use client";

/**
 * /design-preview — Component gallery / design reference page (client component).
 *
 * This route is dev-only and env-flag gated by the server wrapper in page.tsx.
 * See NEXT_PUBLIC_INCLUDE_DESIGN_PREVIEW.
 *
 * Purpose:
 *   - Living reference for every design token (colors, typography)
 *   - Component gallery for every UI primitive
 *   - Contributor-facing design-system doc
 *
 * Do NOT link this from the sidebar or from any user-visible surface.
 */

type Swatch = {
  name: string;
  cssVar: string;
  hex: string;
  role: string;
};

const BACKGROUNDS: Swatch[] = [
  { name: 'canvas', cssVar: '--color-bg-canvas', hex: '#0d1117', role: 'body / page' },
  { name: 'default', cssVar: '--color-bg-default', hex: '#010409', role: 'deepest surface' },
  { name: 'subtle', cssVar: '--color-bg-subtle', hex: '#161b22', role: 'cards, panels' },
  { name: 'elevated', cssVar: '--color-bg-elevated', hex: '#1f2937', role: 'modals, popovers' },
  { name: 'emphasis', cssVar: '--color-bg-emphasis', hex: '#6e7681', role: 'hover on subtle' },
];

const BORDERS: Swatch[] = [
  { name: 'default', cssVar: '--color-border-default', hex: '#30363d', role: 'card borders' },
  { name: 'muted', cssVar: '--color-border-muted', hex: '#21262d', role: 'inner dividers' },
  { name: 'subtle', cssVar: '--color-border-subtle', hex: 'rgba(240,246,252,0.1)', role: 'hairlines' },
];

const FOREGROUNDS: Swatch[] = [
  { name: 'default', cssVar: '--color-fg-default', hex: '#e6edf3', role: 'body text' },
  { name: 'muted', cssVar: '--color-fg-muted', hex: '#7d8590', role: 'secondary text' },
  { name: 'subtle', cssVar: '--color-fg-subtle', hex: '#6e7681', role: 'tertiary / labels' },
];

const ACCENTS: Swatch[] = [
  { name: 'accent-fg', cssVar: '--color-accent-fg', hex: '#2f81f7', role: 'links, active states' },
  { name: 'accent-emphasis', cssVar: '--color-accent-emphasis', hex: '#1f6feb', role: 'primary buttons' },
  { name: 'accent-muted', cssVar: '--color-accent-muted', hex: 'rgba(56,139,253,0.4)', role: 'borders on accent' },
  { name: 'accent-subtle', cssVar: '--color-accent-subtle', hex: 'rgba(56,139,253,0.15)', role: 'backgrounds' },
];

const SEMANTIC: { label: string; swatches: Swatch[] }[] = [
  {
    label: 'success (low severity · healthy · allow)',
    swatches: [
      { name: 'success-fg', cssVar: '--color-success-fg', hex: '#3fb950', role: 'text / icons' },
      { name: 'success-emphasis', cssVar: '--color-success-emphasis', hex: '#238636', role: 'solid pills' },
      { name: 'success-subtle', cssVar: '--color-success-subtle', hex: 'rgba(46,160,67,0.15)', role: 'badge bg' },
    ],
  },
  {
    label: 'attention (medium severity)',
    swatches: [
      { name: 'attention-fg', cssVar: '--color-attention-fg', hex: '#d29922', role: 'text / icons' },
      { name: 'attention-emphasis', cssVar: '--color-attention-emphasis', hex: '#9e6a03', role: 'solid pills' },
      { name: 'attention-subtle', cssVar: '--color-attention-subtle', hex: 'rgba(187,128,9,0.15)', role: 'badge bg' },
    ],
  },
  {
    label: 'severe (high severity)',
    swatches: [
      { name: 'severe-fg', cssVar: '--color-severe-fg', hex: '#db6d28', role: 'text / icons' },
      { name: 'severe-emphasis', cssVar: '--color-severe-emphasis', hex: '#bd561d', role: 'solid pills' },
      { name: 'severe-subtle', cssVar: '--color-severe-subtle', hex: 'rgba(219,109,40,0.15)', role: 'badge bg' },
    ],
  },
  {
    label: 'danger (critical severity · deny · error)',
    swatches: [
      { name: 'danger-fg', cssVar: '--color-danger-fg', hex: '#f85149', role: 'text / icons' },
      { name: 'danger-emphasis', cssVar: '--color-danger-emphasis', hex: '#da3633', role: 'solid pills' },
      { name: 'danger-subtle', cssVar: '--color-danger-subtle', hex: 'rgba(248,81,73,0.15)', role: 'badge bg' },
    ],
  },
  {
    label: 'done (manual review · purple)',
    swatches: [
      { name: 'done-fg', cssVar: '--color-done-fg', hex: '#a371f7', role: 'text / icons' },
      { name: 'done-emphasis', cssVar: '--color-done-emphasis', hex: '#8957e5', role: 'solid pills' },
      { name: 'done-subtle', cssVar: '--color-done-subtle', hex: 'rgba(163,113,247,0.15)', role: 'badge bg' },
    ],
  },
];

function SwatchChip({ swatch }: { swatch: Swatch }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-md border border-[var(--color-border-muted)] bg-[var(--color-bg-subtle)]">
      <div
        className="h-10 w-10 rounded-md border border-[var(--color-border-subtle)] shrink-0"
        style={{ background: `var(${swatch.cssVar})` }}
      />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-xs text-[var(--color-fg-default)]">{swatch.name}</div>
        <div className="font-mono text-[11px] text-[var(--color-fg-muted)] truncate">{swatch.hex}</div>
        <div className="text-[11px] text-[var(--color-fg-subtle)] truncate">{swatch.role}</div>
      </div>
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-12">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-fg-muted)] mb-2">
        {title}
      </h2>
      {description ? (
        <p className="text-sm text-[var(--color-fg-muted)] mb-4">{description}</p>
      ) : null}
      {children}
    </section>
  );
}

/* ---------- Preview components (inlined for now; real primitives arrive in PR 1) ---------- */

type BadgeVariant = 'critical' | 'high' | 'medium' | 'low' | 'allow' | 'deny' | 'manual_review' | 'neutral';

const BADGE_STYLES: Record<BadgeVariant, { fg: string; bg: string; border: string; label: string }> = {
  critical:      { fg: 'var(--color-danger-fg)',     bg: 'var(--color-danger-subtle)',     border: 'var(--color-danger-muted)',     label: 'CRITICAL' },
  high:          { fg: 'var(--color-severe-fg)',     bg: 'var(--color-severe-subtle)',     border: 'var(--color-severe-muted)',     label: 'HIGH' },
  medium:        { fg: 'var(--color-attention-fg)',  bg: 'var(--color-attention-subtle)',  border: 'var(--color-attention-muted)',  label: 'MEDIUM' },
  low:           { fg: 'var(--color-success-fg)',    bg: 'var(--color-success-subtle)',    border: 'var(--color-success-muted)',    label: 'LOW' },
  allow:         { fg: 'var(--color-success-fg)',    bg: 'var(--color-success-subtle)',    border: 'var(--color-success-muted)',    label: 'ALLOW' },
  deny:          { fg: 'var(--color-danger-fg)',     bg: 'var(--color-danger-subtle)',     border: 'var(--color-danger-muted)',     label: 'DENY' },
  manual_review: { fg: 'var(--color-done-fg)',       bg: 'var(--color-done-subtle)',       border: 'var(--color-done-muted)',       label: 'MANUAL REVIEW' },
  neutral:       { fg: 'var(--color-fg-muted)',      bg: 'var(--color-neutral-subtle)',    border: 'var(--color-border-default)',   label: 'NEUTRAL' },
};

function PreviewBadge({ variant }: { variant: BadgeVariant }) {
  const style = BADGE_STYLES[variant];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium font-mono border"
      style={{ color: style.fg, background: style.bg, borderColor: style.border }}
    >
      {style.label}
    </span>
  );
}

function PreviewStatusDot({ status }: { status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown' }) {
  const color =
    status === 'healthy'   ? 'var(--color-success-fg)' :
    status === 'degraded'  ? 'var(--color-attention-fg)' :
    status === 'unhealthy' ? 'var(--color-danger-fg)' :
                             'var(--color-fg-subtle)';
  return (
    <span className="inline-flex items-center gap-2 text-sm text-[var(--color-fg-default)]">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ background: color, boxShadow: `0 0 6px ${color}` }}
      />
      <span className="font-mono text-xs">{status}</span>
    </span>
  );
}

function PreviewMetricTile({
  label,
  value,
  sublabel,
  tone,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  tone?: 'default' | 'critical' | 'success';
}) {
  const valueColor =
    tone === 'critical' ? 'var(--color-danger-fg)' :
    tone === 'success'  ? 'var(--color-success-fg)' :
                          'var(--color-fg-default)';
  return (
    <div className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-subtle)] p-4 min-w-[160px]">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)]">{label}</div>
      <div className="mt-1 font-mono text-2xl leading-none" style={{ color: valueColor }}>{value}</div>
      {sublabel ? <div className="mt-1 text-xs text-[var(--color-fg-subtle)]">{sublabel}</div> : null}
    </div>
  );
}

function PreviewButton({
  variant,
  children,
}: {
  variant: 'primary' | 'secondary' | 'ghost' | 'danger';
  children: React.ReactNode;
}) {
  const styles: Record<string, string> = {
    primary:   'bg-[var(--color-accent-emphasis)] text-[var(--color-fg-on-emphasis)] hover:bg-[var(--color-accent-fg)] border-transparent',
    secondary: 'bg-[var(--color-bg-subtle)] text-[var(--color-fg-default)] hover:bg-[var(--color-bg-elevated)] border-[var(--color-border-default)]',
    ghost:     'bg-transparent text-[var(--color-fg-default)] hover:bg-[var(--color-bg-subtle)] border-transparent',
    danger:    'bg-[var(--color-danger-emphasis)] text-[var(--color-fg-on-emphasis)] hover:bg-[var(--color-danger-fg)] border-transparent',
  };
  return (
    <button className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${styles[variant]}`}>
      {children}
    </button>
  );
}

/* ---------------------------------- Page ---------------------------------- */

export default function DesignPreviewClient() {
  // Server wrapper (page.tsx) already gates on NEXT_PUBLIC_INCLUDE_DESIGN_PREVIEW.
  // No runtime check needed here.

  return (
    <div className="text-[var(--color-fg-default)]">
      <div className="max-w-5xl">
        <header className="mb-12 pb-6 border-b border-[var(--color-border-muted)]">
          <div className="font-mono text-xs text-[var(--color-fg-muted)] mb-2">zdl / design-preview</div>
          <h1 className="text-3xl font-semibold text-[var(--color-fg-default)]">ZDL Design Reference</h1>
          <p className="mt-2 text-sm text-[var(--color-fg-muted)]">
            GitHub Dark (Primer) tokens · Inter body · JetBrains Mono for identifiers. This route is
            dev-only and gated behind <code className="font-mono text-xs">NEXT_PUBLIC_INCLUDE_DESIGN_PREVIEW=true</code>.
          </p>
        </header>

        {/* ---------------------------------- Typography ---------------------------------- */}
        <Section title="Typography" description="Inter sans for body/headings; JetBrains Mono for identifiers, timestamps, JSON, and any number that must line up.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)] mb-3">Sans · Inter</div>
              <div className="space-y-2">
                <div className="text-xs">12 · Aa · The quick brown fox</div>
                <div className="text-sm">14 · Aa · The quick brown fox</div>
                <div className="text-base">16 · Aa · The quick brown fox</div>
                <div className="text-xl">20 · Aa · The quick brown fox</div>
                <div className="text-2xl">24 · Aa · The quick brown fox</div>
                <div className="text-3xl">32 · Aa · The quick brown fox</div>
              </div>
            </div>
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)] mb-3">Mono · JetBrains Mono</div>
              <div className="space-y-2 font-mono">
                <div className="text-xs">12 · CVE-2024-7169</div>
                <div className="text-[13px]">13 · CVE-2024-7169</div>
                <div className="text-sm">14 · CVE-2024-7169</div>
              </div>
              <div className="mt-6 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)] mb-2">Side-by-side</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] text-[var(--color-fg-subtle)] mb-1">sans</div>
                  <div className="text-base">CVE-2024-7169</div>
                </div>
                <div>
                  <div className="text-[11px] text-[var(--color-fg-subtle)] mb-1">mono</div>
                  <div className="text-base font-mono">CVE-2024-7169</div>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ---------------------------------- Backgrounds ---------------------------------- */}
        <Section title="Backgrounds">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {BACKGROUNDS.map((s) => <SwatchChip key={s.name} swatch={s} />)}
          </div>
        </Section>

        {/* ---------------------------------- Borders ---------------------------------- */}
        <Section title="Borders">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {BORDERS.map((s) => <SwatchChip key={s.name} swatch={s} />)}
          </div>
        </Section>

        {/* ---------------------------------- Foreground ---------------------------------- */}
        <Section title="Foreground (text)">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {FOREGROUNDS.map((s) => <SwatchChip key={s.name} swatch={s} />)}
          </div>
        </Section>

        {/* ---------------------------------- Accent ---------------------------------- */}
        <Section title="Accent (GitHub blue)">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {ACCENTS.map((s) => <SwatchChip key={s.name} swatch={s} />)}
          </div>
        </Section>

        {/* ---------------------------------- Semantic ---------------------------------- */}
        <Section title="Semantic colors" description="Only use semantic tokens for meaning — do not use them decoratively.">
          <div className="space-y-6">
            {SEMANTIC.map((group) => (
              <div key={group.label}>
                <div className="text-xs text-[var(--color-fg-muted)] font-mono mb-2">{group.label}</div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {group.swatches.map((s) => <SwatchChip key={s.name} swatch={s} />)}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ---------------------------------- Badges ---------------------------------- */}
        <Section title="Badges — severity" description="Outlined semantic badges with mono labels.">
          <div className="flex flex-wrap gap-2">
            <PreviewBadge variant="critical" />
            <PreviewBadge variant="high" />
            <PreviewBadge variant="medium" />
            <PreviewBadge variant="low" />
          </div>
        </Section>

        <Section title="Badges — governance">
          <div className="flex flex-wrap gap-2">
            <PreviewBadge variant="allow" />
            <PreviewBadge variant="deny" />
            <PreviewBadge variant="manual_review" />
            <PreviewBadge variant="neutral" />
          </div>
        </Section>

        {/* ---------------------------------- Status dots ---------------------------------- */}
        <Section title="Status dots" description="Live system-health indicators with subtle glow.">
          <div className="flex flex-wrap gap-6">
            <PreviewStatusDot status="healthy" />
            <PreviewStatusDot status="degraded" />
            <PreviewStatusDot status="unhealthy" />
            <PreviewStatusDot status="unknown" />
          </div>
        </Section>

        {/* ---------------------------------- Metric tiles ---------------------------------- */}
        <Section title="Metric tiles" description="Pure numbers, no charts.">
          <div className="flex flex-wrap gap-3">
            <PreviewMetricTile label="Findings" value={9} sublabel="9 total in queue" />
            <PreviewMetricTile label="Critical" value={2} tone="critical" sublabel="require immediate action" />
            <PreviewMetricTile label="Manual review" value={4} sublabel="awaiting governance" />
            <PreviewMetricTile label="Auto-approved" value={3} tone="success" sublabel="cleared without review" />
          </div>
        </Section>

        {/* ---------------------------------- Buttons ---------------------------------- */}
        <Section title="Buttons">
          <div className="flex flex-wrap gap-3">
            <PreviewButton variant="primary">Approve</PreviewButton>
            <PreviewButton variant="secondary">Escalate</PreviewButton>
            <PreviewButton variant="ghost">Cancel</PreviewButton>
            <PreviewButton variant="danger">Deny</PreviewButton>
          </div>
        </Section>

        {/* ---------------------------------- Sample card ---------------------------------- */}
        <Section title="Sample card — governance decision" description="How the primitives compose on a real surface.">
          <div className="rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-subtle)] p-6 max-w-3xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="font-mono text-xs text-[var(--color-fg-muted)]">finding · b2c3d4e5-6f70-…</div>
                <h3 className="mt-1 text-lg font-semibold">Governance Decision Status</h3>
              </div>
              <PreviewBadge variant="manual_review" />
            </div>
            <p className="text-sm text-[var(--color-fg-default)] mb-4">
              Policy evaluation requires manual review before remediation can proceed. This asset is an
              internet-facing, tier-0 service that handles ePHI, so it matches three governance rules —{' '}
              <span className="font-mono text-[var(--color-accent-fg)]">manual-review-critical-internet</span>,{' '}
              <span className="font-mono text-[var(--color-accent-fg)]">manual-review-tier0</span>, and{' '}
              <span className="font-mono text-[var(--color-accent-fg)]">manual-review-ephi</span>.
            </p>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)]">Reviewer</div>
                <div className="font-mono mt-1">sec-reviewers@company.com</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-fg-muted)]">Decision score</div>
                <div className="font-mono mt-1">95.0%</div>
              </div>
            </div>
          </div>
        </Section>

        <footer className="mt-16 pt-6 border-t border-[var(--color-border-muted)] font-mono text-xs text-[var(--color-fg-subtle)]">
          zdl design reference · GitHub Dark tokens · updated on frontend rebuild
        </footer>
      </div>
    </div>
  );
}
