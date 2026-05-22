import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        brand: {
          DEFAULT: "#0E5C3A",
          50: "#f0fdf6",
          100: "#d8f0e3",
          200: "#a9e2c5",
          300: "#66c79a",
          400: "#2faa6e",
          500: "#0E5C3A",
          600: "#0b4a2f",
          700: "#083d27",
          800: "#062f1f",
          900: "#042117",
        },
        surface: "var(--surface)",
        "bg-2": "var(--bg-2)",
        line: "var(--line)",
        ink: {
          DEFAULT: "var(--ink)",
          2: "var(--ink-2)",
        },
        cream: {
          50: "#FAFAF7",
          100: "#f3ede2",
          200: "#E5E5DB",
          300: "#d8cebb",
          400: "#9b9485",
          500: "#6f6a5c",
          600: "#3a382f",
          700: "#15140f",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        display: ["var(--font-crimson)", "Georgia", "serif"],
        serif: ["var(--font-crimson)", "Georgia", "serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        body: ["0.9375rem", { lineHeight: "1.6" }],
        "body-lg": ["1rem", { lineHeight: "1.6" }],
      },
      borderRadius: {
        xs: "6px",
        sm: "10px",
        md: "16px",
        lg: "20px",
        xl: "28px",
      },
      spacing: {
        18: "4.5rem",
      },
      transitionDuration: {
        DEFAULT: "200ms",
      },
      transitionTimingFunction: {
        DEFAULT: "ease-out",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        "card-hover": "var(--shadow-md)",
      },
      animation: {
        "fade-up": "fadeUp 600ms ease-out both",
        "page-enter": "pageEnter 420ms ease-out both",
        shimmer: "shimmer 1.6s linear infinite",
        float: "float 5s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pageEnter: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
