import type { Config } from "tailwindcss";

// Forest palette only for v1 (peat / teal alts in design tokens.jsx are unused).
// Source: design_handoff_peatguard/tokens.jsx:6-32 + 87-99 (dark overrides).
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        pg: {
          primary: "#1f4d3a",
          "primary-hover": "#163829",
          "primary-soft": "#e6efeb",
          "primary-fg": "#ffffff",
          accent: "#57a773",
          "accent-soft": "#e0eddf",
          peat: "#3d2818",
          gold: "#c89b3c",
          "gold-soft": "#f5ecd6",
          risk: "#b3261e",
          "risk-soft": "#fae8e6",
          warn: "#e08c0c",
          info: "#2c6e9b",
          surface: "#faf8f3",
          "surface-raised": "#ffffff",
          "surface-sunken": "#f2efe7",
          ink: "#1a1f1c",
          "ink-secondary": "#5a6160",
          "ink-muted": "#8a918f",
          border: "#e3e5e0",
          "border-strong": "#c7ccc4",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": "11px",
        xs: "12px",
        sm: "13px",
        base: "14px",
        md: "15.5px",
        lg: "18px",
        xl: "22px",
        "2xl": "26px",
        "3xl": "32px",
        "4xl": "38px",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "12px",
        xl: "14px",
      },
      boxShadow: {
        raised: "0 1px 2px rgba(20,20,15,0.04), 0 0 0 1px #e3e5e0",
        sticky: "0 4px 12px rgba(20,20,15,0.10)",
        sheet: "0 -8px 24px rgba(20,20,15,0.18)",
        pop: "0 16px 40px rgba(20,20,15,0.18), 0 2px 4px rgba(20,20,15,0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
