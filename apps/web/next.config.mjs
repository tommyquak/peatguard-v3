/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080"}/api/v1/:path*`,
      },
      {
        source: "/cog/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080"}/cog/:path*`,
      },
    ];
  },
};
export default nextConfig;
