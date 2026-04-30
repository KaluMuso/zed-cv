import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        zambian: {
          green: {
            50: "#f0fdf4",
            100: "#d8f0e3",
            200: "#a9e2c5",
            300: "#66c79a",
            400: "#2faa6e",
            500: "#198754",
            600: "#14693f",
            700: "#0f5132",
            800: "#0a3f26",
            900: "#052e1c",
          },
          copper: {
            50: "#fdf4ef",
            100: "#fae3cd",
            200: "#f4c69b",
            300: "#eda56e",
            400: "#d27a3f",
            500: "#b8602a",
            600: "#944f1d",
            700: "#7a3e15",
            800: "#652d16",
            900: "#4a2010",
          },
          orange: {
            50: "#fff7ed",
            100: "#ffedd5",
            200: "#fed7aa",
            300: "#fdba74",
            400: "#fb923c",
            500: "#f97316",
            600: "#ea580c",
            700: "#c2410c",
            800: "#9a3412",
            900: "#7c2d12",
          },
        },
        brand: {
          50: "#f0fdf4",
          100: "#d8f0e3",
          200: "#a9e2c5",
          300: "#66c79a",
          400: "#2faa6e",
          500: "#198754",
          600: "#14693f",
          700: "#0f5132",
          800: "#0a3f26",
          900: "#052e1c",
        },
        /* Warm cream neutrals */
        cream: {
          50: "#faf7f2",
          100: "#f3ede2",
          200: "#e8e1d3",
          300: "#d8cebb",
          400: "#9b9485",
          500: "#6f6a5c",
          600: "#3a382f",
          700: "#15140f",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        display: [
          "var(--font-instrument-serif)",
          "'Times New Roman'",
          "serif",
        ],
        mono: [
          "var(--font-jetbrains-mono)",
          "ui-monospace",
          "monospace",
        ],
      },
      borderRadius: {
        xs: "6px",
        sm: "10px",
        md: "14px",
        lg: "20px",
        xl: "28px",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(20,18,10,0.04), 0 1px 1px rgba(20,18,10,0.03)",
        md: "0 4px 16px -4px rgba(20,18,10,0.08), 0 2px 6px -2px rgba(20,18,10,0.04)",
        lg: "0 18px 40px -12px rgba(20,18,10,0.18), 0 4px 12px -4px rgba(20,18,10,0.08)",
      },
      animation: {
        "fade-up": "fadeUp 600ms cubic-bezier(0.2,0.7,0.2,1) both",
        "page-enter":
          "pageEnter 420ms cubic-bezier(0.2,0.7,0.2,1) both",
        "slide-right":
          "slideRight 500ms cubic-bezier(0.2,0.7,0.2,1) both",
        "scale-in":
          "scaleIn 300ms cubic-bezier(0.2,0.7,0.2,1) both",
        "pulse-ring": "pulseRing 2s ease-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
        spin: "spin 0.8s linear infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pageEnter: {
          from: {
            opacity: "0",
            transform: "translateY(8px)",
            filter: "blur(2px)",
          },
          to: {
            opacity: "1",
            transform: "translateY(0)",
            filter: "blur(0)",
          },
        },
        slideRight: {
          from: { opacity: "0", transform: "translateX(-12px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        scaleIn: {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        pulseRing: {
          "0%": {
            boxShadow: "0 0 0 0 rgba(25,135,84,0.5)",
          },
          "70%": {
            boxShadow: "0 0 0 12px transparent",
          },
          "100%": {
            boxShadow: "0 0 0 0 transparent",
          },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
