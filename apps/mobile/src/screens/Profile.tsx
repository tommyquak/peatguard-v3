// M8 · Profile.
// Source: design_handoff_peatguard/mobile-screens.jsx:493-545.

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Card } from "@/components/Card";
import { Chip } from "@/components/Chip";
import { MobHeader } from "@/components/MobChrome";
import { usePayments, useTasks } from "@/api/client";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import { formatIDR } from "@/lib/format";

const SETTINGS = [
  { icon: "finger-print", label: "Verification & documents", sub: "NIK · selfie · KTP" },
  { icon: "wallet-outline", label: "Payout accounts", sub: "DANA · BRI · PT Pos" },
  { icon: "lock-closed-outline", label: "Privacy & data", sub: "Location history · photos" },
  { icon: "notifications-outline", label: "Notifications", sub: "Push · SMS · voice" },
  { icon: "language-outline", label: "Language", sub: "English" },
] as const;

export function ProfileScreen() {
  const { colors } = useTheme();
  const user = useSession((s) => s.user);
  const villageName = useSession((s) => s.villageName);
  const workerId = useSession((s) => s.workerId);
  const clear = useSession((s) => s.clear);
  const { data: tasks = [] } = useTasks({ worker_id: workerId ?? undefined });
  const payments = usePayments(workerId);

  const totalPaid = (payments.data ?? []).filter((p) => p.status === "released").reduce((s, p) => s + p.amount, 0);
  const tasksDone = tasks.filter((t) => ["paid", "approved"].includes(t.status)).length;
  const approvalRate = tasks.length ? Math.round((tasks.filter((t) => t.status !== "rejected").length / tasks.length) * 100) : 100;

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <MobHeader title="My profile" lead={null} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <View style={{ alignItems: "center", paddingVertical: 14, gap: 10 }}>
          <View style={{ width: 88, height: 88, borderRadius: 44, backgroundColor: "#3d2818", alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: "#fff", fontWeight: "700", fontSize: 26 }}>
              {(user?.name || "SB").slice(0, 2).toUpperCase()}
            </Text>
          </View>
          <View style={{ alignItems: "center" }}>
            <Text style={{ fontSize: 18, fontWeight: "700", color: colors.ink }}>{user?.name || "Worker"}</Text>
            <Text style={{ fontSize: 12, color: colors.inkMuted }}>{villageName ?? "—"} · since Feb 2025</Text>
          </View>
          <View style={{ flexDirection: "row", gap: 6, flexWrap: "wrap", justifyContent: "center" }}>
            <Chip tone="success" size="sm">NIK verified</Chip>
            <Chip tone="gold" size="sm">Team lead</Chip>
            <Chip tone="primary" size="sm">★ 4.8</Chip>
          </View>
        </View>
        <Card pad={0} style={{ overflow: "hidden" }}>
          <View style={{ flexDirection: "row" }}>
            {[
              [tasksDone.toString(), "tasks done"],
              [`${approvalRate}%`, "approval rate"],
              [`${(totalPaid / 1_000_000).toFixed(1)}M`, "total paid"],
            ].map(([v, l], i) => (
              <View
                key={l as string}
                style={{
                  flex: 1, padding: 16, alignItems: "center",
                  borderRightWidth: i < 2 ? 1 : 0, borderRightColor: colors.border,
                }}
              >
                <Text style={{ fontSize: 18, fontWeight: "700", fontFamily: "Menlo", color: colors.ink }}>{v}</Text>
                <Text style={{ fontSize: 11, color: colors.inkMuted, marginTop: 2 }}>{l}</Text>
              </View>
            ))}
          </View>
        </Card>
        <Card pad={0} style={{ overflow: "hidden" }}>
          {SETTINGS.map((s, i) => (
            <Pressable
              key={s.label}
              style={{
                flexDirection: "row", alignItems: "center", gap: 14, padding: 14,
                borderBottomWidth: i < SETTINGS.length - 1 ? 1 : 0,
                borderBottomColor: colors.border,
              }}
            >
              <View style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: colors.surfaceSunken, alignItems: "center", justifyContent: "center" }}>
                <Ionicons name={s.icon as any} size={18} color={colors.primary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13.5, fontWeight: "600", color: colors.ink }}>{s.label}</Text>
                <Text style={{ fontSize: 11.5, color: colors.inkMuted }}>{s.sub}</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={colors.inkMuted} />
            </Pressable>
          ))}
        </Card>
        <Btn kind="ghost" full onPress={() => clear()}>Sign out</Btn>
        <Text style={{ textAlign: "center", fontSize: 11, color: colors.inkMuted, fontFamily: "Menlo", paddingBottom: 8 }}>
          PeatGuard v0.1.0 · {totalPaid ? formatIDR(totalPaid) : ""}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({});
