// Forest palette tokens. Sourced from
// design_handoff_peatguard/tokens.jsx:6-32 (light) + 87-99 (dark overrides).

export const colorsLight = {
  primary: "#1f4d3a",
  primaryHover: "#163829",
  primarySoft: "#e6efeb",
  primaryFg: "#ffffff",
  accent: "#57a773",
  accentSoft: "#e0eddf",
  peat: "#3d2818",
  gold: "#c89b3c",
  goldSoft: "#f5ecd6",
  risk: "#b3261e",
  riskSoft: "#fae8e6",
  warn: "#e08c0c",
  info: "#2c6e9b",
  surface: "#faf8f3",
  surfaceRaised: "#ffffff",
  surfaceSunken: "#f2efe7",
  surfaceInverse: "#1a1f1c",
  ink: "#1a1f1c",
  inkSecondary: "#5a6160",
  inkMuted: "#8a918f",
  border: "#e3e5e0",
  borderStrong: "#c7ccc4",
  shadow: "rgba(20,20,15,0.18)",
};

export const colorsDark = {
  ...colorsLight,
  surface: "#0e1411",
  surfaceRaised: "#161d18",
  surfaceSunken: "#080a09",
  ink: "#f1f3ee",
  inkSecondary: "#a2a8a4",
  inkMuted: "#6c726f",
  border: "#222a25",
  borderStrong: "#3a443d",
  primarySoft: "#0f2419",
  accentSoft: "#0f2419",
  riskSoft: "#2a0d0b",
};

export type Palette = typeof colorsLight;
