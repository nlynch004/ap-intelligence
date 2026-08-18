import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev-only route indicator ("N" badge, bottom-left by default)
  // overlaps the chat input in the demo layout - not needed here, and
  // compile/runtime error overlays still show without it.
  devIndicators: false,
};

export default nextConfig;
