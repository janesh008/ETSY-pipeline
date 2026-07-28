import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "localhost:3000",
    "127.0.0.1:3000",
    "192.168.56.1:3000",
    "192.168.56.1",
    "0.0.0.0:3000",
    "0.0.0.0"
  ],
};

export default nextConfig;
