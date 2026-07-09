/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  reactStrictMode: true,
  // Static HTML export → deployed to S3 and served via CloudFront.
  // The app is fully client-rendered (all data fetching happens in the browser),
  // so no Node server is required. Deep links for the dynamic /finding/[id]
  // route are handled by a CloudFront Function rewrite (see FrontendStack).
  output: 'export',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
