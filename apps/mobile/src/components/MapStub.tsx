import React from "react";
import { View, type ViewStyle } from "react-native";
import Svg, { Defs, Pattern, Path, Rect } from "react-native-svg";
import { useTheme } from "@/theme/useTheme";

// Mobile MapStub: striped peat-tone background to stand in for an MBTiles
// basemap. v1 ships without offline tile caching (handoff §Offline-first #1
// is marked TODO); the stub keeps the screens recognisable in development.

export function MapStub({
  children,
  height = 280,
  style,
  dark,
}: {
  children?: React.ReactNode;
  height?: number;
  style?: ViewStyle;
  dark?: boolean;
}) {
  const { isDark } = useTheme();
  const useDark = dark ?? isDark;
  return (
    <View style={[{ height, position: "relative", overflow: "hidden", backgroundColor: useDark ? "#1f2924" : "#d8d3c0" }, style]}>
      <Svg width="100%" height="100%" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
        <Defs>
          <Pattern id="grid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
            <Path d="M40 0H0v40" fill="none" stroke="rgba(20,20,15,0.18)" strokeWidth="0.5" />
          </Pattern>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#grid)" />
      </Svg>
      <Svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 400 300" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
        <Path d="M0 80 Q80 60 140 90 T260 100 T400 90" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none" />
        <Path d="M0 180 Q90 200 160 175 T320 165 T400 180" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none" />
        <Path d="M120 0 Q130 70 150 130 T180 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none" />
        <Path d="M280 0 Q260 80 270 160 T280 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none" />
      </Svg>
      {children}
    </View>
  );
}

export function Pin({
  x, y, tone, label,
}: { x: number; y: number; tone: "gold" | "info" | "success" | "risk"; label: string }) {
  const colors: Record<typeof tone, string> = { gold: "#c89b3c", info: "#2c6e9b", success: "#57a773", risk: "#b3261e" };
  return (
    <View style={{ position: "absolute", left: `${x}%`, top: `${y}%`, transform: [{ translateX: -32 }, { translateY: -36 }], alignItems: "center" }}>
      <View style={{ paddingHorizontal: 8, paddingVertical: 3, backgroundColor: colors[tone], borderRadius: 999, shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 6, shadowOffset: { width: 0, height: 2 } }}>
        <Svg width={0} height={0}>{/* anchor for label */}</Svg>
        <View style={{ alignItems: "center" }}>
          {/* label rendered via Text in the parent for type safety */}
        </View>
        <PinLabel label={label} />
      </View>
      <View style={{
        width: 0, height: 0,
        borderLeftWidth: 5, borderRightWidth: 5, borderTopWidth: 7,
        borderLeftColor: "transparent", borderRightColor: "transparent",
        borderTopColor: colors[tone],
      }} />
    </View>
  );
}

import { Text } from "react-native";
function PinLabel({ label }: { label: string }) {
  return <Text style={{ color: "#fff", fontSize: 11, fontWeight: "700" }}>{label}</Text>;
}
