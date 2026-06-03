import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          500: "#0E5C3A",
          600: "#0A4A2F",
          700: "#073724",
          foreground: "#FAFAF7",
          DEFAULT: "#0E5C3A",
        },
        accent: {
          100: "#FEF3C7",
          500: "#D97706",
          600: "#B45309",
          DEFAULT: "#D97706",
          foreground: "#FAFAF7",
        },
        surface: {
          DEFAULT: "var(--bg)",
          elevated: "var(--surface)",
          dark: "var(--bg)",
          "dark-elevated": "var(--surface-elevated)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          muted: "var(--muted-2)",
          "2": "var(--ink-2)",
          dark: "var(--ink-dark)",
          "dark-muted": "var(--muted)",
        },
        border: {
          DEFAULT: "hsl(var(--border))",
          dark: "var(--line)",
        },
        success: {
          500: "#16A34A",
          DEFAULT: "#16A34A",
          foreground: "#FAFAF7",
        },
        warning: {
          500: "#F59E0B",
          DEFAULT: "#F59E0B",
          foreground: "#0F172A",
        },
        danger: {
          500: "#DC2626",
          DEFAULT: "#DC2626",
          foreground: "#FFFFFF",
        },
        /* shadcn-style aliases — follow .dark via globals.css HSL channels */
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        /* legacy aliases — migrate to semantic tokens over time */
        brand: {
          50: "#ECFDF5",
          500: "#0E5C3A",
          DEFAULT: "#0E5C3A",
        },
        line: {
          DEFAULT: "var(--line)",
          dark: "var(--line)",
        },
        "bg-2": "var(--bg-2)",
      },
      fontFamily: {
        serif: ['"Crimson Pro"', '"Source Serif Pro"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        display: ['"Crimson Pro"', '"Source Serif Pro"', "Georgia", "serif"],
      },
      fontSize: {
        body: ["0.9375rem", { lineHeight: "1.6" }],
        "body-lg": ["1rem", { lineHeight: "1.6" }],
        "display-sm": [
          "1.875rem",
          { lineHeight: "2.25rem", letterSpacing: "-0.01em" },
        ],
        "display-md": [
          "2.5rem",
          { lineHeight: "2.875rem", letterSpacing: "-0.015em" },
        ],
        "display-lg": [
          "3.5rem",
          { lineHeight: "3.75rem", letterSpacing: "-0.02em" },
        ],
        "display-xl": [
          "4.5rem",
          { lineHeight: "4.625rem", letterSpacing: "-0.025em" },
        ],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },
      boxShadow: {
        soft: "0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04)",
        card: "0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)",
        raised:
          "0 10px 32px -8px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.06)",
        ring: "0 0 0 3px rgba(14, 92, 58, 0.15)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "200ms",
        slow: "320ms",
      },
      transitionTimingFunction: {
        "out-soft": "cubic-bezier(0.22, 0.61, 0.36, 1)",
        "in-soft": "cubic-bezier(0.55, 0.06, 0.68, 0.19)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px) rotate(-2deg)" },
          "50%": { transform: "translateY(-8px) rotate(-1.5deg)" },
        },
        "float-delayed": {
          "0%, 100%": { transform: "translateY(0px) rotate(1.5deg)" },
          "50%": { transform: "translateY(-6px) rotate(2deg)" },
        },
        "float-delay-2": {
          "0%, 100%": { transform: "translateY(0px) rotate(1deg)" },
          "50%": { transform: "translateY(-5px) rotate(1.5deg)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "float-delayed": "float-delayed 7s ease-in-out infinite 0.5s",
        "float-delay-2": "float-delay-2 7s ease-in-out infinite 1s",
        "fade-up": "fade-up 320ms cubic-bezier(0.22, 0.61, 0.36, 1)",
        "fade-in": "fade-in 200ms ease-out",
        "scale-in": "scale-in 200ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        shimmer: "shimmer 2s linear infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
