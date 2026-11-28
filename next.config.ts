import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return process.env.API_PROXY_TARGET
      ? [{ source: "/api/:path*", destination: `${process.env.API_PROXY_TARGET}/api/:path*` }]
      : [];
  },
  poweredByHeader: false,
  async headers() {
    // Static media in /public is not content-hashed, so browsers revalidate daily while Vercel's CDN keeps it
    // for a year; every deployment purges the CDN cache, so a changed file is picked up on the next deploy.
    const staticMedia = [
      { key: "Cache-Control", value: "public, max-age=86400, s-maxage=31536000, stale-while-revalidate=604800" },
    ];
    return [
      { source: "/images/:path*", headers: staticMedia },
      { source: "/brand/:path*", headers: staticMedia },
      { source: "/videos/:path*", headers: staticMedia },
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
        ],
      },
    ];
  },
};

export default nextConfig;

