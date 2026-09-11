import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const hsl = (v: string) => `hsl(var(--${v}))`;

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1400px" } },
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      colors: {
        border: hsl("border"),
        input: hsl("input"),
        ring: hsl("ring"),
        background: hsl("background"),
        foreground: hsl("foreground"),
        primary: {
          DEFAULT: hsl("primary"),
          foreground: hsl("primary-foreground"),
          soft: hsl("primary-soft"),
        },
        lime: { DEFAULT: hsl("accent-lime") },
        secondary: {
          DEFAULT: hsl("secondary"),
          foreground: hsl("secondary-foreground"),
        },
        destructive: {
          DEFAULT: hsl("destructive"),
          foreground: hsl("destructive-foreground"),
        },
        muted: {
          DEFAULT: hsl("muted"),
          foreground: hsl("muted-foreground"),
        },
        accent: {
          DEFAULT: hsl("accent"),
          foreground: hsl("accent-foreground"),
        },
        popover: {
          DEFAULT: hsl("popover"),
          foreground: hsl("popover-foreground"),
        },
        card: {
          DEFAULT: hsl("card"),
          foreground: hsl("card-foreground"),
        },
        success: { DEFAULT: hsl("success"), soft: hsl("success-soft") },
        warning: { DEFAULT: hsl("warning"), soft: hsl("warning-soft") },
        danger: { DEFAULT: hsl("danger"), soft: hsl("danger-soft") },
        info: { DEFAULT: hsl("info"), soft: hsl("info-soft") },
        sidebar: {
          DEFAULT: hsl("sidebar"),
          foreground: hsl("sidebar-foreground"),
          muted: hsl("sidebar-muted"),
          border: hsl("sidebar-border"),
          active: hsl("sidebar-active"),
        },
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        card: "0 1px 2px hsl(var(--shadow-color) / 0.04), 0 4px 16px -8px hsl(var(--shadow-color) / 0.1)",
        pop: "0 8px 30px -12px hsl(var(--shadow-color) / 0.25)",
        glow: "0 0 0 1px hsl(var(--primary) / 0.25), 0 8px 24px -8px hsl(var(--primary) / 0.35)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
