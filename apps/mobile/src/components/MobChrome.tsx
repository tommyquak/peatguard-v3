// Header / tab bar / home indicator -- shared chrome across mobile screens.
// Source: design_handoff_peatguard/mobile-screens.jsx:7-97.

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Pressable, Text, View } from "react-native";
import { useTheme } from "@/theme/useTheme";

export function MobHeader({
  title,
  sub,
  lead = "menu",
  trail,
  onLead,
}: {
  title: string;
  sub?: string;
  lead?: "menu" | "back" | null;
  trail?: React.ReactNode;
  onLead?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        paddingHorizontal: 16,
        paddingTop: 14,
        paddingBottom: 10,
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        backgroundColor: colors.surfaceRaised,
        borderBottomWidth: 1,
        borderBottomColor: colors.border,
      }}
    >
      {lead && (
        <Pressable
          onPress={onLead}
          style={{
            width: 38, height: 38, borderRadius: 10,
            backgroundColor: colors.surfaceSunken,
            alignItems: "center", justifyContent: "center",
          }}
        >
          <Ionicons
            name={lead === "back" ? "chevron-back" : "menu"}
            size={20}
            color={colors.ink}
          />
        </Pressable>
      )}
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: 15.5, fontWeight: "700", letterSpacing: -0.1, color: colors.ink }}>{title}</Text>
        {sub && <Text style={{ fontSize: 11.5, color: colors.inkMuted }}>{sub}</Text>}
      </View>
      {trail}
    </View>
  );
}

export function MobHomeIndicator() {
  return (
    <View style={{ height: 24, alignItems: "center", justifyContent: "center" }}>
      <View style={{ width: 130, height: 4, borderRadius: 2, backgroundColor: "rgba(20,20,15,0.4)" }} />
    </View>
  );
}
