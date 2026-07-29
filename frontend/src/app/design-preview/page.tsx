import { notFound } from 'next/navigation';
import DesignPreviewClient from './DesignPreviewClient';

/**
 * /design-preview — dev-only component gallery.
 *
 * Behavior:
 *   - When NEXT_PUBLIC_INCLUDE_DESIGN_PREVIEW=true (dev only), renders the
 *     full gallery.
 *   - Otherwise (production and default dev), calls notFound() at build time
 *     so the route is not emitted into the static `out/` bundle at all.
 *
 * This keeps the design gallery available locally as a contributor-facing
 * reference without shipping it publicly.
 */
export default function DesignPreviewPage() {
  if (process.env.NEXT_PUBLIC_INCLUDE_DESIGN_PREVIEW !== 'true') {
    notFound();
  }
  return <DesignPreviewClient />;
}
