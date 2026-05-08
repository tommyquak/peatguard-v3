// M6 · Earnings (wallet tab).
// Source: design_handoff_peatguard/mobile-screens.jsx:385-436.

import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Btn } from "@/components/Btn";
import { Chip } from "@/components/Chip";
import { usePayments, useTasks } from "@/api/client";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import { formatIDR } from "@/lib/format";

export function EarningsScreen() {
  const { colors } = useTheme();
  const workerId = useSession((s) => s.workerId);
  const villageId = useSession((s) => s.villageId);
  const payments = usePayments(workerId);
  const { data: tasks = [] } = useTasks({ worker_id: workerId ?? undefined, village_id: villageId ?? undefined });

  const released = (payments.data ?? []).filter((p) => p.status === "released");
  const pending = tasks.filter((t) => ["submitted", "approved"].includes(t.status));
  const totalApproved = released.reduce((s, p) => s + p.amount, 0);
  const pendingTotal = pending.reduce((s, t) => s + t.payout_idr, 0);
  const thisMonth = totalApproved; // simplification for v1

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={{ backgroundColor: colors.primary, paddingHorizontal: 18, paddingTop: 20, paddingBottom: 28, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <Text style={{ fontSize: 14, fontWeight: "700", color: "#fff" }}>Your earnings</Text>
          <Ionicons name="time-outline" size={20} color="#fff" />
        </View>
        <Text style={{ fontSize: 12.5, color: "rgba(255,255,255,0.85)" }}>Total approved</Text>
        <Text style={{ fontSize: 32, fontWeight: "700", fontFamily: "Menlo", letterSpacing: -0.5, color: "#fff", marginTop: 4 }}>
          {formatIDR(totalApproved)}
        </Text>
        <View style={{ flexDirection: "row", gap: 16, marginTop: 12 }}>
          <View>
            <Text style={{ color: "rgba(255,255,255,0.75)", fontSize: 12 }}>This month</Text>
            <Text style={{ color: "#fff", fontWeight: "700", fontFamily: "Menlo", fontSize: 12, marginTop: 2 }}>
              {formatIDR(thisMonth)}
            </Text>
          </View>
          <View style={{ width: 1, backgroundColor: "rgba(255,255,255,0.18)" }} />
          <View>
            <Text style={{ color: "rgba(255,255,255,0.75)", fontSize: 12 }}>Pending</Text>
            <Text style={{ color: "#fff", fontWeight: "700", fontFamily: "Menlo", fontSize: 12, marginTop: 2 }}>
              {formatIDR(pendingTotal)}
            </Text>
          </View>
        </View>
        <View style={{ flexDirection: "row", gap: 8, marginTop: 16 }}>
          <Btn kind="gold" full icon={<Ionicons name="cloud-download-outline" size={18} color="#1a1300" />}>
            Withdraw to DANA
          </Btn>
          <View style={{ width: 50, height: 48, borderRadius: 10, borderWidth: 1, borderColor: "rgba(255,255,255,0.3)", backgroundColor: "rgba(255,255,255,0.1)", alignItems: "center", justifyContent: "center" }}>
            <Ionicons name="settings-outline" size={18} color="#fff" />
          </View>
        </View>
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 8 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>Task history</Text>
          <Chip tone="primary" size="sm">{tasks.length} entries</Chip>
        </View>
        {tasks.map((t) => {
          const paid = released.find((p) => p.task_id === t.id);
          const ok = !!paid;
          return (
            <View key={t.id} style={[styles.row, { backgroundColor: colors.surfaceRaised, borderColor: colors.border }]}>
              <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: ok ? colors.accentSoft : colors.goldSoft, alignItems: "center", justifyContent: "center" }}>
                <Ionicons name={ok ? "checkmark" : "time-outline"} size={16} color={ok ? colors.accent : colors.gold} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 13, fontWeight: "600", color: colors.ink }}>{t.title}</Text>
                <Text style={{ fontSize: 11.5, color: colors.inkMuted }}>
                  {t.deadline.split("T")[0]} · {ok ? "paid to DANA · 47s" : `awaiting ${t.status}`}
                </Text>
              </View>
              <Text style={{ fontFamily: "Menlo", fontWeight: "700", fontSize: 13, color: colors.ink }}>
                Rp {(t.payout_idr / 1000).toFixed(0)}k
              </Text>
            </View>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  row: {
    padding: 12, borderRadius: 12, borderWidth: 1,
    flexDirection: "row", alignItems: "center", gap: 12,
  },
});
