import React from "react";
import { Text, View } from "react-native";
import { useTheme } from "@/theme/useTheme";

type Tone = "neutral" | "primary" | "success" | "risk" | "warn" | "gold" | "info";

export function Chip({
  children,
  tone = "neutral",
  size = "md",
}: {
  children: React.ReactNode;
  tone?: Tone;
  size?: "sm" | "md";
}) {
  const { colors } = useTheme();
  const tones: Record<Tone, { bg: string; fg: string; dot: string }> = {
    neutral: { bg: colors.surfaceSunken, fg: colors.inkSecondary, dot: colors.inkMuted },
    primary: { bg: colors.primarySoft, fg: colors.primary, dot: colors.primary },
    success: { bg: colors.accentSoft, fg: "#2d6e44", dot: colors.accent },
    risk: { bg: colors.riskSoft, fg: colors.risk, dot: colors.risk },
    warn: { bg: "#fdf1d8", fg: "#7a4d00", dot: colors.warn },
    gold: { bg: colors.goldSoft, fg: "#7a5400", dot: colors.gold },
    info: { bg: "#dde9f1", fg: "#1f5278", dot: colors.info },
  };
  const t = tones[tone];
  const sizing = size === "sm"
    ? { h: 20, px: 7, fs: 11, gap: 5 }
    : { h: 24, px: 10, fs: 12, gap: 6 };
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        height: sizing.h,
        paddingHorizontal: sizing.px,
        backgroundColor: t.bg,
        borderRadius: 999,
        gap: sizing.gap,
        alignSelf: "flex-start",
      }}
    >
      <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: t.dot }} />
      <Text style={{ fontSize: sizing.fs, color: t.fg, fontWeight: "700", letterSpacing: -0.1 }}>
        {children}
      </Text>
    </View>
  );
}
