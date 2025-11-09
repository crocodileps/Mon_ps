const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: '/api-backend/:path*',
        destination: 'http://91.98.131.218:8000/:path*',
      },
    ];
  },
}
module.exports = nextConfig
