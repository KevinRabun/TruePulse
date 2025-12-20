/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for SWA deployment
  output: 'export',
  // Trailing slashes for SWA routing compatibility
  trailingSlash: true,
  reactStrictMode: true,
  images: {
    // SWA doesn't support Next.js Image Optimization
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.blob.core.windows.net',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
