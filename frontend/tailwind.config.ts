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
        ink: {
          950: "#0b0a10",
          900: "#131019",
          800: "#1c1826",
          700: "#282235",
        },
      },
    },
  },
  plugins: [],
};

export default config;
