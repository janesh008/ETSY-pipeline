import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "localhost:3000",
    "127.0.0.1:3000",
    "192.168.56.1:3000",
    "192.168.56.1",
  ],
};

export default nextConfig;
