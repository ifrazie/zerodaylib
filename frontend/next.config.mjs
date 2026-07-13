import { PHASE_DEVELOPMENT_SERVER } from 'next/constants.js';

/**
 * @param {string} phase
 * @returns {import('next').NextConfig}
 */
const nextConfig = (phase) => {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;

  return {
    reactStrictMode: true,
    // Static HTML export → deployed to S3 and served via CloudFront.
    // The app is fully client-rendered (all data fetching happens in the browser),
    // so no Node server is required. Deep links for the dynamic /finding/[id]
    // route are handled by a CloudFront Function rewrite (see FrontendStack).
    //
    // `output: 'export'` is applied only for builds. Under `next dev` it is
    // omitted so that /finding/<id> deep links render on demand (dev has no
    // CloudFront rewrite to map them to the exported _shell.html). Production
    // `next build` still produces a pure static export including finding/_shell.
    ...(isDev ? {} : { output: 'export' }),
    images: {
      unoptimized: true,
    },
  };
};

export default nextConfig;
