/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  reactStrictMode: true,
  output: 'standalone',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
