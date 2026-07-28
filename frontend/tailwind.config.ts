import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        spark: {
          50: "#fdf4ff",
          400: "#e879f9",
          500: "#d946ef",
          600: "#c026d3",
          700: "#a21caf",
        },
        // Cyan accent — paired with spark's magenta for the two-tone
        // neon-HUD look (Tron/Blade Runner style), used for focus states,
        // secondary highlights, and gradient endpoints.
        volt: {
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
        },
        ink: {
          950: "#0b0a10",
          900: "#131019",
          800: "#1c1826",
          700: "#282235",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
      },
      keyframes: {
        "grid-pan": {
          "0%": { backgroundPosition: "0px 0px" },
          "100%": { backgroundPosition: "48px 48px" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "grid-pan": "grid-pan 6s linear infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
