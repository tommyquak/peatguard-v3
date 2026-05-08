// M2 · Home / Map (light + dark via system colour scheme).
// Source: design_handoff_peatguard/mobile-screens.jsx:100-185.

import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import React, { useState } from "react";
import {
  Pressable, RefreshControl, ScrollView, StyleSheet, Text, View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Chip } from "@/components/Chip";
import { MapStub } from "@/components/MapStub";
import { useTasks } from "@/api/client";
import type { Task } from "@/api/types";
import { useSession } from "@/store/session";
import { useTheme } from "@/theme/useTheme";
import { formatIDRShort } from "@/lib/format";
import type { RootStackParamList } from "@/navigation/types";

const PIN_TONES: Record<Task["status"], string> = {
  available: "#c89b3c",
  accepted: "#2c6e9b",
  submitted: "#57a773",
  approved: "#57a773",
  rejected: "#b3261e",
  paid: "#8a918f",
};

export function HomeScreen() {
  const { colors, isDark } = useTheme();
  const villageId = useSession((s) => s.villageId);
  const villageName = useSession((s) => s.villageName);
  const user = useSession((s) => s.user);
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const tasksQ = useTasks({ village_id: villageId ?? undefined });
  const tasks = (tasksQ.data ?? []).filter((t) => t.status !== "paid");
  const [refreshing, setRefreshing] = useState(false);

  async function onRefresh() {
    setRefreshing(true);
    try {
      await tasksQ.refetch();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={[styles.header, { backgroundColor: colors.surfaceRaised, borderBottomColor: colors.border }]}>
        <View style={styles.avatar}>
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 13 }}>
            {(user?.name || "SB").slice(0, 2).toUpperCase()}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>
            Good morning, {user?.name?.split(" ")[0] || "there"}
          </Text>
          <Text style={{ fontSize: 11.5, color: colors.inkMuted }}>
            {villageName ?? "—"} · {tasks.filter((t) => t.status === "available").length} tasks available
          </Text>
        </View>
        <Pressable
          style={[styles.iconBtn, { backgroundColor: colors.surfaceSunken }]}
          onPress={() => (navigation as any).navigate("Tabs", { screen: "Messages" })}
        >
          <Ionicons name="notifications-outline" size={18} color={colors.ink} />
          <View style={[styles.dot, { backgroundColor: colors.risk }]} />
        </Pressable>
      </View>

      <View style={{ height: 280, position: "relative" }}>
        <MapStub dark={isDark} height={280}>
          {tasks.slice(0, 4).map((t, i) => (
            <Pin
              key={t.id}
              x={20 + (i % 3) * 28}
              y={22 + (i % 2) * 30}
              tone={PIN_TONES[t.status]}
              label={t.status === "accepted" ? "Active" : formatIDRShort(t.payout_idr)}
              onPress={() => navigation.navigate("TaskDetail", { taskId: t.id })}
            />
          ))}
          <View style={{ position: "absolute", top: 12, left: 12, right: 12, flexDirection: "row", gap: 6 }}>
            <Chip size="sm" tone="gold">{tasks.filter((t) => t.status === "available").length} available</Chip>
            <Chip size="sm" tone="info">{tasks.filter((t) => t.status === "accepted").length} active</Chip>
            <View style={{ marginLeft: "auto", paddingHorizontal: 8, paddingVertical: 4, backgroundColor: "rgba(255,255,255,0.9)", borderRadius: 6, flexDirection: "row", alignItems: "center", gap: 4 }}>
              <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: "#57a773" }} />
              <Text style={{ fontSize: 11, fontWeight: "600", color: "#1a1f1c" }}>Offline OK</Text>
            </View>
          </View>
        </MapStub>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 14, gap: 10 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 4 }}>
          <Text style={{ fontSize: 14, fontWeight: "700", color: colors.ink }}>Tasks near you</Text>
          <Text style={{ fontSize: 12, color: colors.inkMuted }}>Pull to refresh</Text>
        </View>
        {tasks.length === 0 && (
          <Text style={{ color: colors.inkMuted, padding: 24, textAlign: "center" }}>
            No tasks in your village yet. The operator will publish new tasks here as canal_risk priorities change.
          </Text>
        )}
        {tasks.map((t) => (
          <TaskCard key={t.id} task={t} onPress={() => navigation.navigate("TaskDetail", { taskId: t.id })} />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function Pin({
  x, y, tone, label, onPress,
}: { x: number; y: number; tone: string; label: string; onPress?: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={{ position: "absolute", left: `${x}%`, top: `${y}%`, alignItems: "center" }}
    >
      <View style={{ paddingHorizontal: 8, paddingVertical: 3, backgroundColor: tone, borderRadius: 999 }}>
        <Text style={{ color: "#fff", fontSize: 11, fontWeight: "700" }}>{label}</Text>
      </View>
      <View style={{ width: 0, height: 0, borderLeftWidth: 5, borderRightWidth: 5, borderTopWidth: 7, borderLeftColor: "transparent", borderRightColor: "transparent", borderTopColor: tone }} />
    </Pressable>
  );
}

function TaskCard({ task, onPress }: { task: Task; onPress: () => void }) {
  const { colors } = useTheme();
  const tones: Record<Task["status"], { c: string; l: string }> = {
    available: { c: "#c89b3c", l: "Available" },
    accepted: { c: "#2c6e9b", l: "Accepted" },
    submitted: { c: "#57a773", l: "Submitted" },
    approved: { c: "#57a773", l: "Approved" },
    rejected: { c: "#b3261e", l: "Rejected" },
    paid: { c: "#8a918f", l: "Paid" },
  };
  const t = tones[task.status];
  return (
    <Pressable
      onPress={onPress}
      style={{
        padding: 14, backgroundColor: colors.surfaceRaised,
        borderColor: colors.border, borderWidth: 1, borderRadius: 14,
        flexDirection: "row", gap: 12, alignItems: "flex-start",
      }}
    >
      <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.goldSoft, alignItems: "center", justifyContent: "center" }}>
        <Ionicons name="shield-outline" size={22} color={t.c} />
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 3 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: t.c }} />
            <Text style={{ fontSize: 10.5, fontWeight: "700", color: t.c, textTransform: "uppercase", letterSpacing: 0.5 }}>{t.l}</Text>
          </View>
          <Text style={{ fontSize: 11, color: colors.inkMuted }}>· {task.deadline.split("T")[0]}</Text>
        </View>
        <Text style={{ fontSize: 14.5, fontWeight: "700", color: colors.ink }}>{task.title}</Text>
        <Text style={{ fontSize: 12, color: colors.inkMuted, marginTop: 2 }}>{task.sub ?? task.aoi_code}</Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={{ fontSize: 16, fontWeight: "700", fontFamily: "Menlo", color: colors.ink }}>
          {formatIDRShort(task.payout_idr)}
        </Text>
        <Ionicons name="chevron-forward" size={16} color={colors.inkMuted} style={{ marginTop: 4 }} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: 16, paddingVertical: 12,
    flexDirection: "row", alignItems: "center", gap: 10,
    borderBottomWidth: 1,
  },
  avatar: {
    width: 38, height: 38, borderRadius: 19,
    backgroundColor: "#3d2818",
    alignItems: "center", justifyContent: "center",
  },
  iconBtn: {
    width: 38, height: 38, borderRadius: 10,
    alignItems: "center", justifyContent: "center", position: "relative",
  },
  dot: { position: "absolute", top: 6, right: 6, width: 8, height: 8, borderRadius: 4 },
});
