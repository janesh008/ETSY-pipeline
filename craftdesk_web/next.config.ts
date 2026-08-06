import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false, // Prevents React 18 dev double-mount from firing useEffect twice (no effect in production)
  allowedDevOrigins: [
    "localhost:3000",
    "127.0.0.1:3000",
    "192.168.56.1:3000",
    "192.168.56.1",
    "0.0.0.0:3000",
    "0.0.0.0",
    "34.139.213.233",
    "34.139.213.233:3000",
  ],

  // Keep HTTP connections alive to FastAPI — prevents premature socket close
  // that causes ECONNRESET on long LLM generation calls (60–120 s).
  httpAgentOptions: {
    keepAlive: true,
  },

  // Proxy all /api/* requests through Next.js server → FastAPI on port 8000.
  // This means the browser only ever talks to port 3000 — port 8000 never
  // needs to be publicly exposed (works identically on local & GCP VM).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
