/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api-backend/:path*',
        destination: 'http://91.98.131.218:8001/:path*',
      },
    ];
  },
}

module.exports = nextConfig
