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
