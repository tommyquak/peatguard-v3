import React from "react";
import Svg, { Circle, Path, Rect } from "react-native-svg";

// Port of design_handoff_peatguard/web-screens-1.jsx:69-78.
export function Logomark({ size = 32 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32">
      <Rect width="32" height="32" rx="8" fill="#1f4d3a" />
      <Path d="M8 22c0-4 3-7 6-7 4 0 4 4 8 4 2 0 4-1 4-1v6H8z" fill="#57a773" />
      <Circle cx="22" cy="11" r="2.5" fill="#c89b3c" />
      <Path d="M8 22c0-4 3-7 6-7 4 0 4 4 8 4 2 0 4-1 4-1" stroke="rgba(255,255,255,0.4)" strokeWidth="0.6" fill="none" />
    </Svg>
  );
}
