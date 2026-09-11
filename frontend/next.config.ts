import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Keep the dev-mode indicator away from the sidebar's user card.
  devIndicators: { buildActivityPosition: "bottom-right" },
};

export default nextConfig;
