import type { NextConfig } from "next";
import { readFileSync } from "fs";
import { resolve } from "path";

let appVersion = "0.0.0";
try {
  appVersion = readFileSync(resolve(__dirname, "../VERSION"), "utf-8").trim();
} catch {
  // Fallback if VERSION file not found
}

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:5556/api/:path*",
      },
    ];
  },
};

export default nextConfig;
