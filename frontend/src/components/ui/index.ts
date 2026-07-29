/**
 * Barrel export for the shared UI primitives.
 *
 * Import from '@/components/ui' rather than reaching into individual files:
 *   import { Badge, Mono, MetricTile } from '@/components/ui';
 */

export { Badge } from './Badge';
export type { BadgeVariant, BadgeProps } from './Badge';

export { StatusDot } from './StatusDot';
export type { Status, StatusDotProps } from './StatusDot';

export { MetricTile } from './MetricTile';
export type { MetricTileProps, MetricTone } from './MetricTile';

export { SectionHeader } from './SectionHeader';
export type { SectionHeaderProps } from './SectionHeader';

export { DataTable } from './DataTable';
export type { DataTableProps, Column } from './DataTable';

export { Mono } from './Mono';
export type { MonoProps } from './Mono';
