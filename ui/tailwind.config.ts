import type { Config } from "tailwindcss";

/**
 * Design tokens for a fraud operations console.
 *
 * The audience is people who look at risk tooling all day, so this deliberately
 * reads like Radar or Datadog rather than a product landing page: one accent
 * colour, hairline borders, small radii, near-flat shadows, and colour reserved
 * for meaning (caught / escaped / held) instead of decoration. There is no
 * gradient, blur, or glow token here on purpose. Every number in this app is a
 * measurement, and decoration competes with it for attention.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces, coolest to warmest.
        canvas: "#f7f8fa",
        surface: "#ffffff",
        subtle: "#f2f4f7",
        line: "#e4e7ec",
        "line-strong": "#d0d5dd",

        ink: {
          DEFAULT: "#101828",
          soft: "#475467",
          faint: "#667085",
          ghost: "#98a2b3",
        },

        // The single accent. Used for interactive affordances and nothing else.
        accent: {
          50: "#eff4ff",
          100: "#d1e0ff",
          200: "#b2ccff",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
        },

        // Semantic status. These carry meaning and must not be used decoratively.
        danger: { 50: "#fef3f2", 200: "#fecdca", 500: "#d92d20", 700: "#912018" },
        success: { 50: "#ecfdf3", 200: "#abefc6", 500: "#079455", 700: "#085d3a" },
        warn: { 50: "#fffaeb", 200: "#fedf89", 500: "#dc6803", 700: "#93370d" },

        // Red team versus blue team, kept distinct from danger/accent so an
        // attacker-coloured element is never mistaken for an error state.
        red: { DEFAULT: "#d92d20", soft: "#fecdca", ink: "#912018" },
        blue: { DEFAULT: "#1d4ed8", soft: "#b2ccff", ink: "#1e40af" },
      },

      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },

      // Console radii. Nothing rounder than 8px.
      borderRadius: {
        DEFAULT: "4px",
        md: "6px",
        lg: "8px",
      },

      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,0.05)",
        raised: "0 2px 6px rgba(16,24,40,0.07)",
        // Focus ring, the only "glow" in the system.
        focus: "0 0 0 3px rgba(37,99,235,0.18)",
      },

      fontSize: {
        "2xs": ["10px", { lineHeight: "14px" }],
        xs: ["11px", { lineHeight: "16px" }],
        sm: ["12px", { lineHeight: "18px" }],
        base: ["13px", { lineHeight: "20px" }],
        md: ["14px", { lineHeight: "21px" }],
        lg: ["16px", { lineHeight: "24px" }],
        xl: ["20px", { lineHeight: "28px" }],
        "2xl": ["24px", { lineHeight: "32px" }],
      },

      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        // Indeterminate progress for a running pipeline stage.
        indeterminate: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(400%)" },
        },
        // Travelling dash on the loop diagram. Runs only while a loop is active,
        // so it reports state rather than decorating the page.
        "loop-dash": {
          to: { strokeDashoffset: "-28" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.18s ease-out both",
        indeterminate: "indeterminate 1.1s ease-in-out infinite",
        "loop-dash": "loop-dash 1s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
