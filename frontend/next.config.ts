import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  transpilePackages: ["@splinetool/runtime"],
  webpack(config, { webpack }) {
    // Spline's full runtime contains optional boolean/Draco loaders whose
    // binaries are not included in the published npm package. TermPilot's
    // procedural primitive rig uses neither feature, so exclude those dead
    // branches instead of making the production build depend on missing files.
    config.plugins.push(
      new webpack.IgnorePlugin({
        resourceRegExp: /(?:boolean_wasm_bg\.wasm|libs\/draco\/(?:gltf\/)?(?:draco_decoder\.wasm|draco_wasm_wrapper\.js|draco_decoder\.js))$/,
      }),
    );
    return config;
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          {
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(), geolocation=(), display-capture=(), xr-spatial-tracking=(self)",
          },
          { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive, nosnippet" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
        ],
      },
    ];
  },
  async rewrites() {
    if (process.env.VERCEL) return [];
    const backend = (process.env.API_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000").replace(
      /\/$/,
      "",
    );
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
