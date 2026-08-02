import type { NextConfig } from "next";

const backendOriginRaw = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
const backendOrigin = backendOriginRaw.replace(/\/$/, "");

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
