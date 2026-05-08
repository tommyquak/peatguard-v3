import React from "react";
import { View, type ViewStyle } from "react-native";
import { radii } from "@/theme/space";
import { useTheme } from "@/theme/useTheme";

export function Card({
  children,
  style,
  pad = 14,
}: {
  children: React.ReactNode;
  style?: ViewStyle;
  pad?: number;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: colors.surfaceRaised,
          borderColor: colors.border,
          borderWidth: 1,
          borderRadius: radii.lg,
          padding: pad,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}
