import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Keep the dev-mode indicator away from the sidebar's user card.
  devIndicators: { buildActivityPosition: "bottom-right" },
  webpack(config) {
    // Resolve the "@/" import alias to THIS app's source root. Explicit absolute path
    // so the alias works regardless of how TsconfigPathsPlugin computes the base
    // (which differs when Vercel builds under its Turbo presets).
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": path.resolve(process.cwd(), "."),
    };
    return config;
  },
};

export default nextConfig;
