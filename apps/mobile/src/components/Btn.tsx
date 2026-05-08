import React from "react";
import { Pressable, StyleSheet, Text, View, type ViewStyle } from "react-native";
import { useTheme } from "@/theme/useTheme";
import { radii } from "@/theme/space";

type Kind = "primary" | "secondary" | "ghost" | "soft" | "danger" | "success" | "gold";
type Size = "sm" | "md" | "lg";

export function Btn({
  children,
  kind = "primary",
  size = "lg",
  full,
  onPress,
  disabled,
  icon,
  iconRight,
  style,
}: {
  children?: React.ReactNode;
  kind?: Kind;
  size?: Size;
  full?: boolean;
  onPress?: () => void;
  disabled?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  style?: ViewStyle;
}) {
  const { colors } = useTheme();
  const kinds: Record<Kind, { bg: string; fg: string; bd: string }> = {
    primary: { bg: colors.primary, fg: colors.primaryFg, bd: colors.primary },
    secondary: { bg: colors.surfaceRaised, fg: colors.ink, bd: colors.borderStrong },
    ghost: { bg: "transparent", fg: colors.ink, bd: "transparent" },
    soft: { bg: colors.primarySoft, fg: colors.primary, bd: "transparent" },
    danger: { bg: colors.risk, fg: "#fff", bd: colors.risk },
    success: { bg: colors.accent, fg: "#fff", bd: colors.accent },
    gold: { bg: colors.gold, fg: "#1a1300", bd: colors.gold },
  };
  const sizes: Record<Size, { h: number; px: number; fs: number; gap: number; r: number }> = {
    sm: { h: 30, px: 10, fs: 12.5, gap: 6, r: radii.sm },
    md: { h: 38, px: 14, fs: 13.5, gap: 8, r: radii.sm },
    lg: { h: 48, px: 18, fs: 15, gap: 10, r: radii.md },
  };
  const k = kinds[kind];
  const s = sizes[size];
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        {
          height: s.h,
          paddingHorizontal: s.px,
          gap: s.gap,
          borderRadius: s.r,
          backgroundColor: k.bg,
          borderColor: k.bd,
          width: full ? "100%" : undefined,
          opacity: disabled ? 0.5 : pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      {icon}
      {children !== undefined && children !== null && (
        <Text style={{ fontSize: s.fs, fontWeight: "600", color: k.fg, letterSpacing: -0.1 }}>{children}</Text>
      )}
      {iconRight}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
});
