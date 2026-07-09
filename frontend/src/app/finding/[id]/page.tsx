import FindingDetailClient from './FindingDetailClient';

/**
 * Server component wrapper for the client-rendered finding detail view.
 *
 * Under `output: 'export'`, Next.js requires `generateStaticParams()` for every
 * dynamic segment. Finding IDs are runtime UUIDs from CockroachDB and are not
 * known at build time, so we emit a single shell page at `finding/_shell.html`
 * that the CloudFront Function rewrites every `/finding/<id>` deep link to. The
 * actual data is fetched client-side by FindingDetailClient using the id parsed
 * from the URL at runtime.
 *
 * A concrete placeholder id (rather than a bracketed segment) is used so the
 * exported filename is a plain `_shell.html`, which is portable across build
 * hosts (bracketed filenames are not reliably written on all platforms).
 */
export function generateStaticParams(): { id: string }[] {
  return [{ id: '_shell' }];
}

// output: 'export' has no runtime server, so unmatched params cannot be
// rendered on demand. The CloudFront rewrite maps them to the shell above.
export const dynamicParams = false;

interface FindingDetailPageProps {
  params: {
    id: string;
  };
}

export default function FindingDetailPage({ params }: FindingDetailPageProps) {
  return <FindingDetailClient id={params.id} />;
}
