import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#071019",
        raised: "#0D1822",
        panel: "#111E29",
        ink: "#E8F0F5",
        mute: "#8FA3B3",
        steel: "#263846",
        cyan: "#37C7F4",
        go: "#3DDC97",
        warn: "#F5B942",
        stop: "#FF5D5D",
        wait: "#A78BFA",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
